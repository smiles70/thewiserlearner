"""Tests for `pipeline.captions` (pure logic, no whisper)."""

from __future__ import annotations

from pipeline import captions

# --------------------------------------------------------------------------- #
# wrap_to_lines                                                               #
# --------------------------------------------------------------------------- #


def test_wrap_to_lines_respects_max_chars():
    text = "This is a fairly short line that should fit within the limit."
    lines = captions.wrap_to_lines(text, max_chars=20)
    assert all(len(line) <= 20 for line in lines)
    assert " ".join(lines) == text


def test_wrap_to_lines_handles_long_word_alone_on_line():
    lines = captions.wrap_to_lines("supercalifragilisticexpialidocious word", max_chars=10)
    assert lines[0] == "supercalifragilisticexpialidocious"
    assert lines[1] == "word"


def test_wrap_to_lines_empty_input_returns_empty_list():
    assert captions.wrap_to_lines("") == []


# --------------------------------------------------------------------------- #
# chunk_lines_into_cues                                                       #
# --------------------------------------------------------------------------- #


def test_chunk_lines_into_cues_two_lines_per_cue_default():
    lines = ["A", "B", "C", "D", "E"]
    cues = captions.chunk_lines_into_cues(lines)
    assert cues == [["A", "B"], ["C", "D"], ["E"]]


# --------------------------------------------------------------------------- #
# distribute_durations                                                        #
# --------------------------------------------------------------------------- #


def test_distribute_durations_sums_to_total_when_minimums_fit():
    out = captions.distribute_durations([2, 4, 4], total_seconds=20.0)
    assert sum(out) == 20.0
    # bigger word counts get more time
    assert out[1] > out[0]


def test_distribute_durations_honours_minimum_when_total_too_short():
    # 3 cues each minimum 1.5 s = 4.5 s total minimum; total of 1.0 s is too small
    out = captions.distribute_durations([1, 1, 1], total_seconds=1.0)
    assert all(d >= captions.MIN_CUE_SECONDS for d in out)


def test_distribute_durations_empty_returns_empty():
    assert captions.distribute_durations([], total_seconds=10.0) == []


# --------------------------------------------------------------------------- #
# min_cue_seconds                                                             #
# --------------------------------------------------------------------------- #


def test_min_cue_seconds_floor_is_min_cue_seconds_constant():
    assert captions.min_cue_seconds(0) == captions.MIN_CUE_SECONDS
    assert captions.min_cue_seconds(2) == captions.MIN_CUE_SECONDS  # 2 * 0.375 = 0.75 < 1.5


def test_min_cue_seconds_scales_with_word_count_above_floor():
    # 10 words * 0.375 = 3.75 s
    assert captions.min_cue_seconds(10) == 3.75


# --------------------------------------------------------------------------- #
# format_srt / format_vtt                                                     #
# --------------------------------------------------------------------------- #


def _sample_cues():
    return [
        captions.Cue(index=1, start_seconds=0.0, end_seconds=2.5, lines=["Hello,"]),
        captions.Cue(index=2, start_seconds=2.5, end_seconds=5.0, lines=["world.", "Welcome."]),
    ]


def test_format_srt_uses_comma_timestamp_separator():
    out = captions.format_srt(_sample_cues())
    assert "00:00:00,000 --> 00:00:02,500" in out
    assert "00:00:02,500 --> 00:00:05,000" in out
    assert "1\n" in out and "2\n" in out


def test_format_vtt_starts_with_webvtt_header_and_uses_dot_separator():
    out = captions.format_vtt(_sample_cues())
    assert out.startswith("WEBVTT\n")
    assert "00:00:02.500 --> 00:00:05.000" in out


def test_format_srt_two_line_cue_emits_both_lines():
    out = captions.format_srt(_sample_cues())
    assert "world.\nWelcome." in out


# --------------------------------------------------------------------------- #
# Flesch-Kincaid                                                              #
# --------------------------------------------------------------------------- #


def test_flesch_kincaid_grade_returns_zero_for_empty_text():
    assert captions.flesch_kincaid_grade("") == 0.0


def test_flesch_kincaid_grade_simple_text_below_grade_9():
    text = "We will draft a short note. It is easy to do. You will see how."
    assert captions.flesch_kincaid_grade(text) <= 9.0


def test_flesch_kincaid_grade_complex_text_above_grade_9():
    text = (
        "Conventional implementation strategies necessitate sophisticated "
        "infrastructural commitments before substantive operational benefits "
        "materialise."
    )
    assert captions.flesch_kincaid_grade(text) > 9.0


# --------------------------------------------------------------------------- #
# build_cues_from_beats                                                       #
# --------------------------------------------------------------------------- #


def test_build_cues_from_beats_emits_monotonic_cues_per_beat():
    beats = {
        "hook": "Today we draft a short note.",
        "acknowledge": "You may wonder if it sounds like you.",
        "why": "It saves time.",
        "show": "Watch me do it.",
        "walkthrough": ["Step one.", "Step two.", "Step three."],
        "recover": "If it misunderstands, ask again.",
        "recap": "You have now drafted a note.",
        "outro": "Thanks for following along.",
    }
    timings = {
        "hook": (0.0, 4.0),
        "acknowledge": (4.0, 4.0),
        "why": (8.0, 2.0),
        "show": (10.0, 2.0),
        "walkthrough": (12.0, 6.0),
        "recover": (18.0, 4.0),
        "recap": (22.0, 3.0),
        "outro": (25.0, 3.0),
    }
    cues = captions.build_cues_from_beats(beats, timings)
    assert cues, "expected at least one cue"
    # Indices monotonically increase from 1
    assert [c.index for c in cues] == list(range(1, len(cues) + 1))
    # End times monotonically increase
    starts = [c.start_seconds for c in cues]
    assert starts == sorted(starts)
    # Each cue meets the minimum-duration floor
    for c in cues:
        assert c.end_seconds - c.start_seconds >= captions.MIN_CUE_SECONDS - 1e-6
