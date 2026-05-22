"""Tests for `pipeline.storyboard` — composition.yaml schema and loader.

These tests pin the schema before the parser is implemented. They are the
executable spec for what counts as a valid composition manifest.

Contract clauses encoded here:
  - C-3.4   all 8 REQUIRED_BEATS in canonical order
  - C-3.4#5 walkthrough has >= 2 named steps
  - C-6.2   body font >= 48 px, headings >= 72 px at 1080p
  - C-6.3   text/background contrast >= 7:1
  - C-6.5   transitions between 400 and 800 ms
  - C-6.6   on-screen text dwell >= max(3, words*0.4 + 1) seconds
  - C-6.8   walkthrough step cards expose a `prior_anchor` slot
  - C-6.9   pilots are faceless (default flag in visual_theme)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pipeline import storyboard

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #

VALID_YAML = """\
format: 1920x1080
fps: 25
visual_theme:
  palette: warm-neutral-morning-light
  mood: calm, dignified, quiet
  faceless: true
  no_text_in_image: true
transitions:
  default_ms: 600
  min_ms: 400
  max_ms: 800
beats:
  - beat: hook
    image_prompt: "A softly-lit kitchen table with a phone, warm morning light."
    title: "AI Is Everywhere Now"
    subtitle: "A calm map of where it already lives."
    title_font_px: 88
    body_font_px: 56
    contrast_ratio: 16.9
    dwell_seconds: 30.0
  - beat: acknowledge
    image_prompt: "Quiet hands on a wooden surface, soft daylight."
    title: "The names sound similar."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 28.0
  - beat: why
    image_prompt: "An open map on a table, gentle shadow."
    title: "The choice is yours."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 18.0
  - beat: show
    image_prompt: "A weather app on a phone, calm composition."
    title: "One minute of your day."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 24.0
  - beat: walkthrough
    image_prompt: "Four objects on a wooden table: speaker, phone, camera, envelope."
    title: "Four places AI lives."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 60.0
    steps:
      - index: 1
        text: "Part one. The voice assistants."
        dwell_seconds: 15.0
      - index: 2
        text: "Part two. The chat assistants."
        prior_anchor: "1. Voice assistants"
        dwell_seconds: 15.0
      - index: 3
        text: "Part three. The picture helpers."
        prior_anchor: "2. Chat assistants"
        dwell_seconds: 15.0
      - index: 4
        text: "Part four. The AI inside apps."
        prior_anchor: "3. Picture helpers"
        dwell_seconds: 15.0
  - beat: recover
    image_prompt: "A single cup of tea on a quiet kitchen counter."
    title: "Pick one. The rest can wait."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 20.0
  - beat: recap
    image_prompt: "A simple printed map with four labels."
    title: "Voice. Chat. Pictures. Apps."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 18.0
  - beat: outro
    image_prompt: "An older adult's hand resting near an open notebook."
    title: "Thank you for being here."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 14.0
    dwell_seconds: 14.0
"""


@pytest.fixture
def write_yaml(tmp_path: Path):
    def _w(text: str) -> Path:
        p = tmp_path / "composition.yaml"
        p.write_text(textwrap.dedent(text), encoding="utf-8")
        return p

    return _w


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


def test_valid_composition_loads(write_yaml):
    comp = storyboard.load_composition(write_yaml(VALID_YAML))
    assert comp.format == "1920x1080"
    assert comp.fps == 25
    assert len(comp.beats) == 8
    assert [b.beat for b in comp.beats] == list(storyboard.REQUIRED_BEATS)


def test_walkthrough_beat_has_steps(write_yaml):
    comp = storyboard.load_composition(write_yaml(VALID_YAML))
    walk = next(b for b in comp.beats if b.beat == "walkthrough")
    assert len(walk.steps) == 4
    assert walk.steps[0].index == 1
    # C-6.8: every step beyond the first carries a prior_anchor
    assert all(s.prior_anchor is not None for s in walk.steps[1:])


def test_visual_theme_defaults_to_faceless(write_yaml):
    comp = storyboard.load_composition(write_yaml(VALID_YAML))
    assert comp.visual_theme.faceless is True


# --------------------------------------------------------------------------- #
# Negative cases                                                              #
# --------------------------------------------------------------------------- #


def test_missing_beat_fails(write_yaml):
    bad = VALID_YAML.replace("  - beat: recap\n", "").replace(
        '    title: "Voice. Chat. Pictures. Apps."\n', ""
    )
    # remove the rest of the recap block too
    bad = "\n".join(
        line
        for line in bad.splitlines()
        if not (line.startswith("    ") and "recap" not in line and "Voice." in line)
    )
    # simplest: just drop the recap stanza entirely
    bad_yaml = (
        VALID_YAML.split("  - beat: recap")[0]
        + VALID_YAML.split("  - beat: outro")[0]
        .split("  - beat: recap")[1]
        .partition("  - beat: outro")[0]
        + "  - beat: outro"
        + VALID_YAML.split("  - beat: outro")[1]
    )
    # easier: programmatically delete the recap block
    lines = VALID_YAML.splitlines(keepends=True)
    out: list[str] = []
    skip = False
    for line in lines:
        if line.startswith("  - beat: recap"):
            skip = True
            continue
        if skip and line.startswith("  - beat: "):
            skip = False
        if not skip:
            out.append(line)
    bad_yaml = "".join(out)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "recap" in str(exc.value).lower()


def test_wrong_beat_order_fails(write_yaml):
    # Swap `why` and `show` blocks
    parts = VALID_YAML.split("  - beat: ")
    # parts[0] is preamble, parts[1..8] are the 8 beat blocks
    assert parts[3].startswith("why")
    assert parts[4].startswith("show")
    parts[3], parts[4] = parts[4], parts[3]
    bad_yaml = "  - beat: ".join(parts)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "order" in str(exc.value).lower()


def test_walkthrough_with_one_step_fails(write_yaml):
    bad_yaml = (
        VALID_YAML.replace(
            '      - index: 2\n        text: "Part two. The chat assistants."\n'
            '        prior_anchor: "1. Voice assistants"\n        dwell_seconds: 15.0\n',
            "",
        )
        .replace(
            '      - index: 3\n        text: "Part three. The picture helpers."\n'
            '        prior_anchor: "2. Chat assistants"\n        dwell_seconds: 15.0\n',
            "",
        )
        .replace(
            '      - index: 4\n        text: "Part four. The AI inside apps."\n'
            '        prior_anchor: "3. Picture helpers"\n        dwell_seconds: 15.0\n',
            "",
        )
    )
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "walkthrough" in str(exc.value).lower()


def test_title_font_below_72_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("title_font_px: 88", "title_font_px: 60", 1)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "72" in str(exc.value) or "title_font_px" in str(exc.value)


def test_body_font_below_48_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("body_font_px: 56", "body_font_px: 40", 1)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "48" in str(exc.value) or "body_font_px" in str(exc.value)


def test_contrast_below_7_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("contrast_ratio: 16.9", "contrast_ratio: 4.5", 1)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "7" in str(exc.value) or "contrast" in str(exc.value).lower()


def test_transition_below_400ms_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("default_ms: 600", "default_ms: 200")
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "400" in str(exc.value) or "transition" in str(exc.value).lower()


def test_transition_above_800ms_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("default_ms: 600", "default_ms: 1200")
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "800" in str(exc.value) or "transition" in str(exc.value).lower()


def test_dwell_below_three_seconds_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("dwell_seconds: 30.0", "dwell_seconds: 1.5", 1)
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "dwell" in str(exc.value).lower() or "3" in str(exc.value)


def test_unknown_beat_name_fails(write_yaml):
    bad_yaml = VALID_YAML.replace("- beat: hook", "- beat: prologue", 1)
    with pytest.raises(storyboard.CompositionError):
        storyboard.load_composition(write_yaml(bad_yaml))


def test_steps_outside_walkthrough_fails(write_yaml):
    # Add a steps block to the hook beat where it doesn't belong.
    bad_yaml = VALID_YAML.replace(
        "    dwell_seconds: 30.0\n  - beat: acknowledge",
        "    dwell_seconds: 30.0\n    steps:\n"
        "      - index: 1\n        text: 'Bogus'\n        dwell_seconds: 5.0\n"
        "  - beat: acknowledge",
    )
    with pytest.raises(storyboard.CompositionError) as exc:
        storyboard.load_composition(write_yaml(bad_yaml))
    assert "walkthrough" in str(exc.value).lower() or "steps" in str(exc.value).lower()


# --------------------------------------------------------------------------- #
# Cross-module invariants                                                     #
# --------------------------------------------------------------------------- #


def test_beat_names_align_with_audit_module():
    """The storyboard schema must use exactly the same beat names as the
    auditor and TTS planner, otherwise voice.json timings won't map."""
    from pipeline.audit import REQUIRED_BEATS as AUDIT_BEATS

    assert storyboard.REQUIRED_BEATS == AUDIT_BEATS


def test_format_constant_matches_compositor():
    """Composition format must agree with the compositor's frame size."""
    from pipeline import compositor

    expected = f"{compositor.VIDEO_WIDTH}x{compositor.VIDEO_HEIGHT}"
    comp = storyboard.load_composition_from_string(VALID_YAML)
    assert comp.format == expected


# --------------------------------------------------------------------------- #
# Worked examples in SKILL.md must validate                                   #
# --------------------------------------------------------------------------- #

import re  # noqa: E402

SKILL_PATH = Path(__file__).resolve().parent.parent / "skills" / "visual-director" / "SKILL.md"

_FENCE_RE = re.compile(r"^```yaml\s*\n(.*?)^```", re.DOTALL | re.MULTILINE)


def _extract_yaml_blocks(md_text: str) -> list[str]:
    return [m.group(1) for m in _FENCE_RE.finditer(md_text)]


def test_skill_md_contains_at_least_two_worked_examples():
    blocks = _extract_yaml_blocks(SKILL_PATH.read_text(encoding="utf-8"))
    assert len(blocks) >= 2, (
        f"skills/visual-director/SKILL.md must contain at least two YAML "
        f"worked examples; found {len(blocks)}"
    )


def test_every_worked_example_in_skill_md_validates():
    """Examples in the skill are the few-shot prompt for Claude. If they
    fail the schema, the skill is teaching the model the wrong pattern."""
    blocks = _extract_yaml_blocks(SKILL_PATH.read_text(encoding="utf-8"))
    for i, block in enumerate(blocks, start=1):
        try:
            storyboard.load_composition_from_string(block)
        except storyboard.CompositionError as exc:
            raise AssertionError(
                f"worked example #{i} in SKILL.md failed validation:\n{exc}"
            ) from exc
