"""Tests for the v0.2 compositor functions: pure logic only, no ffmpeg."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pipeline import compositor, storyboard, visuals
from tests.test_storyboard import VALID_YAML

# --------------------------------------------------------------------------- #
# build_ffmpeg_command_multi (pure)                                           #
# --------------------------------------------------------------------------- #


def _seg(path: str, dur: float) -> compositor.Segment:
    return compositor.Segment(image_path=Path(path), duration_seconds=dur)


def test_multi_command_rejects_empty_segments():
    with pytest.raises(ValueError, match="at least one segment"):
        compositor.build_ffmpeg_command_multi([], Path("v.wav"), None, 600, Path("o.mp4"))


def test_multi_command_rejects_xfade_below_400ms():
    with pytest.raises(ValueError, match=r"400.*800"):
        compositor.build_ffmpeg_command_multi(
            [_seg("a.png", 5.0)], Path("v.wav"), None, 200, Path("o.mp4")
        )


def test_multi_command_rejects_xfade_above_800ms():
    with pytest.raises(ValueError, match=r"400.*800"):
        compositor.build_ffmpeg_command_multi(
            [_seg("a.png", 5.0)], Path("v.wav"), None, 1200, Path("o.mp4")
        )


def test_multi_command_one_input_per_segment_plus_voice():
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0), _seg("c.png", 5.0)]
    cmd = compositor.build_ffmpeg_command_multi(segs, Path("voice.wav"), None, 600, Path("out.mp4"))
    # Each segment contributes exactly one '-i <png>'; voice contributes one
    # additional '-i voice.wav'.
    assert cmd.count("-i") == len(segs) + 1
    assert "voice.wav" in cmd
    for s in segs:
        assert str(s.image_path) in cmd


def test_multi_command_xfade_offsets_for_variable_durations():
    """offset_k = sum(T_0..T_{k-1}) - k*X.

    For T = [4.0, 6.0, 5.0] and X = 0.6:
      offset_1 = 4.0 - 0.6 = 3.400
      offset_2 = (4.0 + 6.0) - 1.2 = 8.800
    """
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0), _seg("c.png", 5.0)]
    cmd = compositor.build_ffmpeg_command_multi(segs, Path("voice.wav"), None, 600, Path("out.mp4"))
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "offset=3.400" in fc
    assert "offset=8.800" in fc
    # xfade duration must be exactly 600 ms.
    assert "duration=0.600" in fc


def test_multi_command_omits_subtitles_when_no_captions():
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0)]
    cmd = compositor.build_ffmpeg_command_multi(segs, Path("voice.wav"), None, 600, Path("out.mp4"))
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "subtitles=" not in fc
    # the final video stream should be mapped from the last xfade label
    assert "[x1]" in cmd[cmd.index("-map") + 1]


def test_multi_command_includes_subtitles_filter_when_captions_present():
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0)]
    cmd = compositor.build_ffmpeg_command_multi(
        segs, Path("voice.wav"), Path("captions.srt"), 600, Path("out.mp4")
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "subtitles='captions.srt'" in fc
    assert "Alignment=2" in fc  # bottom-centre, matches v0.1 styling


def test_multi_command_escapes_windows_paths_in_subtitles():
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0)]
    cmd = compositor.build_ffmpeg_command_multi(
        segs, Path("v.wav"), Path(r"C:\episodes\foo\captions.srt"), 600, Path("o.mp4")
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "C\\:/episodes/foo/captions.srt" in fc


def test_multi_command_single_segment_has_no_xfade():
    """A composition with only one beat (degenerate but valid) maps directly
    from [v0] without any xfade chain."""
    cmd = compositor.build_ffmpeg_command_multi(
        [_seg("a.png", 4.0)], Path("v.wav"), None, 600, Path("o.mp4")
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade" not in fc
    assert cmd[cmd.index("-map") + 1] == "[v0]"


def test_multi_command_audio_map_index_matches_segment_count():
    """The voice input is at index N (after N image inputs); the audio map
    must reference that exact index."""
    segs = [_seg("a.png", 4.0), _seg("b.png", 6.0), _seg("c.png", 5.0)]
    cmd = compositor.build_ffmpeg_command_multi(segs, Path("v.wav"), None, 600, Path("o.mp4"))
    audio_maps = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-map"]
    # second -map is the audio map
    assert audio_maps[1] == f"{len(segs)}:a"


def test_multi_command_uses_h264_aac_yuv420p_faststart():
    """Codec choices must mirror v0.1 for YouTube delivery parity."""
    cmd = compositor.build_ffmpeg_command_multi(
        [_seg("a.png", 4.0), _seg("b.png", 4.0)],
        Path("v.wav"),
        None,
        600,
        Path("o.mp4"),
    )
    assert "libx264" in cmd
    assert "aac" in cmd
    assert "yuv420p" in cmd
    assert "+faststart" in cmd


def test_multi_command_zoompan_uses_d_equals_1():
    """The spike validated d=1 is the correct zoompan idiom; regression-fence
    that here so a future refactor cannot reintroduce d=total_frames bug."""
    cmd = compositor.build_ffmpeg_command_multi(
        [_seg("a.png", 4.0), _seg("b.png", 4.0)],
        Path("v.wav"),
        None,
        600,
        Path("o.mp4"),
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "zoompan=" in fc
    assert ":d=1:" in fc


# --------------------------------------------------------------------------- #
# expand_segments                                                             #
# --------------------------------------------------------------------------- #


def test_expand_segments_produces_seven_plus_steps_count(tmp_path: Path):
    """For E-001-shaped composition (4 walkthrough steps), expand_segments
    must yield 7 + 4 = 11 segments."""
    comp = storyboard.load_composition_from_string(VALID_YAML)
    vis = visuals.generate_all(comp, tmp_path)
    voice_timings = {name: 30.0 for name in storyboard.REQUIRED_BEATS}
    segs = compositor.expand_segments(comp, vis, voice_timings, tmp_path)
    assert len(segs) == 7 + 4  # 7 non-walkthrough + 4 walkthrough steps
    # Walkthrough sub-segments are contiguous and indexed 1..N.
    walk_segs = [s for s in segs if s.beat == "walkthrough"]
    assert [s.step_index for s in walk_segs] == [1, 2, 3, 4]


def test_expand_segments_walkthrough_durations_sum_to_voice_duration(tmp_path: Path):
    """Per-step durations are distributed proportionally to declared dwell;
    the total must match the walkthrough beat's voice duration to keep the
    timeline aligned with captions."""
    comp = storyboard.load_composition_from_string(VALID_YAML)
    vis = visuals.generate_all(comp, tmp_path)
    voice_timings = {name: 30.0 for name in storyboard.REQUIRED_BEATS}
    voice_timings["walkthrough"] = 80.0
    segs = compositor.expand_segments(comp, vis, voice_timings, tmp_path)
    walk_total = sum(s.duration_seconds for s in segs if s.beat == "walkthrough")
    assert walk_total == pytest.approx(80.0, rel=1e-6)


def test_expand_segments_uses_voice_timing_when_present(tmp_path: Path):
    comp = storyboard.load_composition_from_string(VALID_YAML)
    vis = visuals.generate_all(comp, tmp_path)
    voice_timings = {"hook": 41.5, "acknowledge": 40.0}  # rest missing
    segs = compositor.expand_segments(comp, vis, voice_timings, tmp_path)
    by_beat = {s.beat: s for s in segs if s.beat != "walkthrough"}
    assert by_beat["hook"].duration_seconds == pytest.approx(41.5)
    assert by_beat["acknowledge"].duration_seconds == pytest.approx(40.0)
    # Beats absent from voice_timings fall back to composition.dwell_seconds.
    assert by_beat["why"].duration_seconds == pytest.approx(18.0)  # from VALID_YAML


# --------------------------------------------------------------------------- #
# Step-overlay rendering (Pillow only)                                        #
# --------------------------------------------------------------------------- #


def test_walkthrough_overlay_renders_full_hd_png(tmp_path: Path):
    from PIL import Image

    base = tmp_path / "base.png"
    Image.new("RGB", (1920, 1080), (18, 22, 28)).save(base, "PNG")
    out = tmp_path / "step.png"
    compositor.render_walkthrough_step_overlay(
        base,
        out,
        step_index=2,
        step_text="Type one sentence about what you want to say.",
        prior_anchor="1. Open Claude on your phone.",
        title="Four small steps.",
    )
    assert out.is_file()
    assert Image.open(out).size == (1920, 1080)


def test_walkthrough_overlay_step_one_has_no_anchor_footer(tmp_path: Path):
    """Step 1 has no prior step; the renderer must accept prior_anchor=None
    without crashing."""
    from PIL import Image

    base = tmp_path / "base.png"
    Image.new("RGB", (1920, 1080), (18, 22, 28)).save(base, "PNG")
    out = tmp_path / "step1.png"
    compositor.render_walkthrough_step_overlay(
        base,
        out,
        step_index=1,
        step_text="Open the Claude app.",
        prior_anchor=None,
        title="Four small steps.",
    )
    assert out.is_file()


# --------------------------------------------------------------------------- #
# Integration with default_composition (offline end-to-end logic)             #
# --------------------------------------------------------------------------- #


GOOD_SCRIPT = """\
---
id: E-INT
title: "Integration Test"
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
  recover: "A short recovery line for the test."
  recap: "If you have followed along, you have now seen the test."
  outro: "Thank you for following along with the test."
---
"""


def test_full_v2_pipeline_integration_offline(tmp_path: Path):
    """Default composition + LocalProvider + expand_segments + ffmpeg-command
    builder must all compose end-to-end without errors. This proves the v0.2
    glue is internally consistent before we run a real ffmpeg render."""
    ep = tmp_path / "E-INT"
    ep.mkdir()
    (ep / "script.md").write_text(textwrap.dedent(GOOD_SCRIPT).lstrip(), encoding="utf-8")
    voice_json = {
        "beats": [
            {"name": "hook", "start_seconds": 0.0, "duration_seconds": 30.0},
            {"name": "acknowledge", "start_seconds": 30.0, "duration_seconds": 25.0},
            {"name": "why", "start_seconds": 55.0, "duration_seconds": 18.0},
            {"name": "show", "start_seconds": 73.0, "duration_seconds": 26.0},
            {"name": "walkthrough", "start_seconds": 99.0, "duration_seconds": 80.0},
            {"name": "recover", "start_seconds": 179.0, "duration_seconds": 22.0},
            {"name": "recap", "start_seconds": 201.0, "duration_seconds": 20.0},
            {"name": "outro", "start_seconds": 221.0, "duration_seconds": 19.0},
        ]
    }
    (ep / "voice.json").write_text(json.dumps(voice_json), encoding="utf-8")

    comp = storyboard.default_composition(ep / "script.md", ep / "voice.json")
    vis = visuals.generate_all(comp, ep)
    voice_timings = {b["name"]: b["duration_seconds"] for b in voice_json["beats"]}
    segs = compositor.expand_segments(comp, vis, voice_timings, ep)
    cmd = compositor.build_ffmpeg_command_multi(
        segs,
        ep / "voice.wav",  # not a real file, but the builder is pure
        None,
        comp.transitions.default_ms,
        ep / "episode.mp4",
    )
    # 7 non-walkthrough + 2 walkthrough steps = 9 segments.
    assert len(segs) == 9
    assert cmd.count("-i") == 9 + 1  # 9 images + 1 voice
    # All beat backgrounds and step variants exist on disk.
    for s in segs:
        assert s.image_path.is_file()
