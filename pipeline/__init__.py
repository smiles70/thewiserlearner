"""The Wiser Learner production pipeline.

Modules:
    audit       — contract auditor (deterministic + agent stub)
    tts         — text-to-speech wrapper (Edge TTS)
    captions    — Whisper-driven caption generation and lint
    compositor  — FFmpeg-based video assembly
    youtube     — YouTube Data API publisher (stubbed)
    run_episode — end-to-end orchestrator
    cli         — command-line entry points
"""

__version__ = "0.1.0"
