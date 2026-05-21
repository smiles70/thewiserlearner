"""Tests for `pipeline.tts.build_plan` (pure planning logic, no network)."""

from __future__ import annotations

from pipeline import tts

SAMPLE_BEATS = {
    "hook": "Today we will draft a short note.",
    "acknowledge": "You may be wondering if it sounds like you.",
    "why": "It saves time and keeps your voice in the message.",
    "show": "Watch me do it once.",
    "walkthrough": [
        "Step one.",
        "Step two.",
        "Step three.",
    ],
    "recover": "If it misunderstands, ask again with one small change.",
    "recap": "You have now drafted a short note.",
    "outro": "Thanks for following along.",
}


def test_walkthrough_steps_become_separate_segments():
    plan = tts.build_plan(SAMPLE_BEATS)
    walk_speech = [s for s in plan.segments if s.kind == "speech" and s.name.startswith("walk_")]
    assert len(walk_speech) == 3


def test_inter_step_pauses_inserted():
    plan = tts.build_plan(SAMPLE_BEATS)
    walk_pauses = [
        s for s in plan.segments if s.kind == "silence" and s.name.startswith("walk_pause_")
    ]
    # 3 steps -> 2 inter-step pauses
    assert len(walk_pauses) == 2
    assert all(s.duration_ms == tts.INTER_STEP_PAUSE_MS for s in walk_pauses)


def test_inter_beat_pauses_between_each_beat():
    plan = tts.build_plan(SAMPLE_BEATS)
    beat_pauses = [
        s
        for s in plan.segments
        if s.kind == "silence"
        and s.name.endswith("_pause")
        and not s.name.startswith("walk_pause_")
    ]
    # 8 beats -> 7 inter-beat pauses (none after the final beat)
    assert len(beat_pauses) == 7
    assert all(s.duration_ms == tts.INTER_BEAT_PAUSE_MS for s in beat_pauses)


def test_beat_segment_ranges_cover_all_eight_beats():
    plan = tts.build_plan(SAMPLE_BEATS)
    assert set(plan.beat_segment_ranges.keys()) == set(tts.REQUIRED_BEATS)
    for start, end in plan.beat_segment_ranges.values():
        assert end > start


def test_empty_beats_skipped():
    beats = dict(SAMPLE_BEATS)
    beats["acknowledge"] = ""
    plan = tts.build_plan(beats)
    assert "acknowledge" not in plan.beat_segment_ranges


def test_walkthrough_string_treated_as_single_step():
    beats = dict(SAMPLE_BEATS)
    beats["walkthrough"] = "Just one step."
    plan = tts.build_plan(beats)
    walk_speech = [s for s in plan.segments if s.kind == "speech" and s.name.startswith("walk_")]
    assert len(walk_speech) == 1


def test_compute_beat_timings_returns_monotonic_starts():
    plan = tts.build_plan(SAMPLE_BEATS)
    durations = [1.0] * len(plan.segments)
    timings = tts._compute_beat_timings(plan, durations)
    starts = [t.start_seconds for t in timings]
    assert starts == sorted(starts)
    assert all(t.duration_seconds > 0 for t in timings)
