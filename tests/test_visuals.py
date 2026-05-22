"""Tests for `pipeline.visuals` (LocalProvider + generate_all)
and `pipeline.storyboard.default_composition`."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pipeline import storyboard, visuals
from tests.test_storyboard import VALID_YAML

GOOD_SCRIPT = """\
---
id: E-TEST
title: "Test Episode"
target_runtime_seconds: 240
target_wpm: 110
ai_episode: false
mynaani_mention: false
cta_subscribe: true
risk_topics: [none]
verified_claims: []
beats:
  hook: "A short hook line for the test."
  acknowledge: "A short acknowledgement line for the test."
  why: "A short reason line for the test."
  show: "A short demonstration narration line for the test."
  walkthrough:
    - "Part one. The first numbered step."
    - "Part two. The second numbered step."
    - "Part three. The third numbered step."
  recover: "A short recovery line for the test."
  recap: "If you have followed along, you have now seen the test."
  outro: "Thank you for following along with the test."
---
"""

VOICE_JSON = {
    "script_path": "ignored",
    "voice": "en-US-AriaNeural",
    "rate": "-25%",
    "pitch": "+0Hz",
    "duration_seconds": 240.0,
    "integrated_lufs": -16.0,
    "true_peak_dbtp": -1.5,
    "beats": [
        {"name": "hook", "start_seconds": 0.0, "duration_seconds": 30.0},
        {"name": "acknowledge", "start_seconds": 30.0, "duration_seconds": 25.0},
        {"name": "why", "start_seconds": 55.0, "duration_seconds": 18.0},
        {"name": "show", "start_seconds": 73.0, "duration_seconds": 26.0},
        {"name": "walkthrough", "start_seconds": 99.0, "duration_seconds": 80.0},
        {"name": "recover", "start_seconds": 179.0, "duration_seconds": 22.0},
        {"name": "recap", "start_seconds": 201.0, "duration_seconds": 20.0},
        {"name": "outro", "start_seconds": 221.0, "duration_seconds": 19.0},
    ],
}


@pytest.fixture
def episode_dir(tmp_path: Path) -> Path:
    d = tmp_path / "E-TEST"
    d.mkdir()
    (d / "script.md").write_text(textwrap.dedent(GOOD_SCRIPT).lstrip(), encoding="utf-8")
    (d / "voice.json").write_text(json.dumps(VOICE_JSON), encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# default_composition                                                         #
# --------------------------------------------------------------------------- #


def test_default_composition_validates_against_schema(episode_dir):
    comp = storyboard.default_composition(
        episode_dir / "script.md",
        episode_dir / "voice.json",
    )
    # If this round-trips through model_validate without raising, the
    # default is contract-clean.
    storyboard.Composition.model_validate(comp.model_dump())


def test_default_composition_has_eight_beats_in_order(episode_dir):
    comp = storyboard.default_composition(
        episode_dir / "script.md",
        episode_dir / "voice.json",
    )
    assert [b.beat for b in comp.beats] == list(storyboard.REQUIRED_BEATS)


def test_default_composition_walkthrough_step_count_matches_script(episode_dir):
    comp = storyboard.default_composition(
        episode_dir / "script.md",
        episode_dir / "voice.json",
    )
    walk = next(b for b in comp.beats if b.beat == "walkthrough")
    assert len(walk.steps) == 3  # GOOD_SCRIPT has three walkthrough entries
    # C-6.8: every step beyond the first carries a prior anchor.
    assert all(s.prior_anchor is not None for s in walk.steps[1:])


def test_default_composition_inherits_voice_durations(episode_dir):
    comp = storyboard.default_composition(
        episode_dir / "script.md",
        episode_dir / "voice.json",
    )
    by_name = {b.beat: b for b in comp.beats}
    assert by_name["hook"].dwell_seconds == pytest.approx(30.0)
    assert by_name["walkthrough"].dwell_seconds == pytest.approx(80.0)


def test_default_composition_minimum_dwell_floor(episode_dir):
    """Even if voice timing is below 3 s, dwell must clamp to MIN_DWELL_SECONDS."""
    voice = json.loads((episode_dir / "voice.json").read_text(encoding="utf-8"))
    voice["beats"][0]["duration_seconds"] = 0.5
    (episode_dir / "voice.json").write_text(json.dumps(voice), encoding="utf-8")
    comp = storyboard.default_composition(
        episode_dir / "script.md",
        episode_dir / "voice.json",
    )
    assert comp.beats[0].dwell_seconds >= storyboard.MIN_DWELL_SECONDS


# --------------------------------------------------------------------------- #
# LocalProvider                                                               #
# --------------------------------------------------------------------------- #


def test_local_provider_emits_a_full_hd_png(tmp_path: Path):
    from PIL import Image

    provider = visuals.LocalProvider()
    comp = storyboard.load_composition_from_string(VALID_YAML)
    out_path = tmp_path / "hook.png"
    result = provider.generate(comp.beats[0], comp.visual_theme, out_path)
    assert result == out_path
    assert out_path.is_file()
    img = Image.open(out_path)
    assert img.size == (visuals.CARD_WIDTH, visuals.CARD_HEIGHT)
    assert img.mode == "RGB"


def test_local_provider_is_deterministic(tmp_path: Path):
    """Same beat + theme -> identical bytes. Required for reproducible
    pipeline runs and for diffability of episode artefacts in git LFS."""
    provider = visuals.LocalProvider()
    comp = storyboard.load_composition_from_string(VALID_YAML)
    p1 = provider.generate(comp.beats[0], comp.visual_theme, tmp_path / "a.png")
    p2 = provider.generate(comp.beats[0], comp.visual_theme, tmp_path / "b.png")
    assert p1.read_bytes() == p2.read_bytes()


def test_local_provider_distinguishes_beats(tmp_path: Path):
    """Different beat names produce different orb positions, hence different
    bytes. Without this, every card looks identical and the pipeline regresses
    to the v0.1 single-card behaviour."""
    provider = visuals.LocalProvider()
    comp = storyboard.load_composition_from_string(VALID_YAML)
    paths: list[Path] = []
    for beat in comp.beats[:3]:
        paths.append(provider.generate(beat, comp.visual_theme, tmp_path / f"{beat.beat}.png"))
    digests = {p.read_bytes() for p in paths}
    assert len(digests) == 3


def test_unknown_palette_falls_back_to_default(tmp_path: Path):
    """The visual-director skill is free to invent palette names; the
    LocalProvider must never crash on an unknown one."""
    top, bottom = visuals.palette_to_colors("not-a-real-palette-name")
    assert (top, bottom) == visuals.DEFAULT_PALETTE


# --------------------------------------------------------------------------- #
# generate_all orchestration                                                  #
# --------------------------------------------------------------------------- #


def test_generate_all_emits_one_png_per_beat(tmp_path: Path):
    comp = storyboard.load_composition_from_string(VALID_YAML)
    results = visuals.generate_all(comp, tmp_path)
    assert set(results) == set(storyboard.REQUIRED_BEATS)
    for beat_name, vr in results.items():
        assert vr.image_path == tmp_path / "visuals" / f"{beat_name}.png"
        assert vr.image_path.is_file()
        assert vr.width == visuals.CARD_WIDTH
        assert vr.height == visuals.CARD_HEIGHT


def test_generate_all_rejects_a_silent_failure(tmp_path: Path):
    """If a provider claims success but produces a 0-byte file, generate_all
    must raise rather than let the compositor swallow the error."""

    class BrokenProvider:
        def generate(self, beat, theme, out_path):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"")  # 0-byte "success"
            return out_path

    comp = storyboard.load_composition_from_string(VALID_YAML)
    with pytest.raises(RuntimeError, match="unusably small"):
        visuals.generate_all(comp, tmp_path, provider=BrokenProvider())
