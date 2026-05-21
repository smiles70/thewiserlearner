"""Tests for `pipeline.compositor` (pure logic; no ffmpeg invocation)."""

from __future__ import annotations

from pathlib import Path

from pipeline import compositor


def test_build_ffmpeg_command_includes_loop_input_and_voice():
    cmd = compositor.build_ffmpeg_command(
        Path("card.png"), Path("voice.wav"), None, Path("out.mp4")
    )
    assert "-loop" in cmd and "1" in cmd
    assert "card.png" in cmd
    assert "voice.wav" in cmd
    assert cmd[-1] == "out.mp4"


def test_build_ffmpeg_command_uses_h264_aac_yuv420p():
    cmd = compositor.build_ffmpeg_command(Path("c.png"), Path("v.wav"), None, Path("o.mp4"))
    assert "libx264" in cmd
    assert "aac" in cmd
    assert "yuv420p" in cmd
    assert "+faststart" in cmd


def test_build_ffmpeg_command_omits_subtitles_filter_when_no_captions():
    cmd = compositor.build_ffmpeg_command(Path("c.png"), Path("v.wav"), None, Path("o.mp4"))
    assert "-vf" not in cmd


def test_build_ffmpeg_command_includes_subtitles_filter_when_captions_present():
    cmd = compositor.build_ffmpeg_command(
        Path("c.png"), Path("v.wav"), Path("captions.srt"), Path("o.mp4")
    )
    assert "-vf" in cmd
    vf_index = cmd.index("-vf") + 1
    assert "subtitles=" in cmd[vf_index]
    assert "captions.srt" in cmd[vf_index]
    assert "Alignment=2" in cmd[vf_index]  # bottom-centre


def test_build_ffmpeg_command_escapes_windows_paths_in_subtitle_filter():
    cmd = compositor.build_ffmpeg_command(
        Path("c.png"), Path("v.wav"), Path(r"C:\episodes\foo\captions.srt"), Path("o.mp4")
    )
    vf_index = cmd.index("-vf") + 1
    assert "C\\:/episodes/foo/captions.srt" in cmd[vf_index]


def test_video_dimensions_are_full_hd_at_25_fps():
    assert compositor.VIDEO_WIDTH == 1920
    assert compositor.VIDEO_HEIGHT == 1080
    assert compositor.VIDEO_FPS == 25


def test_typography_meets_contract_minimums():
    # Contract C-6.2: heading >= 72 px, body >= 48 px at 1080p.
    assert compositor.TITLE_FONT_PX >= 72
    assert compositor.SUBTITLE_FONT_PX >= 48


def _luminance(rgb):
    """Relative luminance per WCAG 2.x."""

    def chan(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(a, b):
    la, lb = _luminance(a), _luminance(b)
    light, dark = max(la, lb), min(la, lb)
    return (light + 0.05) / (dark + 0.05)


def test_foreground_background_contrast_meets_aaa():
    # Contract C-6.3: minimum 7:1 for normal text (WCAG AAA).
    ratio = _contrast_ratio(compositor.FOREGROUND_RGB, compositor.BACKGROUND_RGB)
    assert ratio >= 7.0
