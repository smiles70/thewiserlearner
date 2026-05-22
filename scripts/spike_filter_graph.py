"""Empirical spike: validate the ffmpeg filter graph for v0.2 visuals.

Run before touching pipeline/compositor.py. Renders three dummy 1920x1080 PNG
cards into a single MP4 with:

  - per-segment Ken Burns (slow zoompan, ~5% over the segment)
  - xfade crossfade transitions between segments (500 ms, mid-range of the
    C-6.5 400-800 ms window)
  - burned-in subtitles from a small inline SRT

Success criteria:
  1. ffmpeg exits 0
  2. Output MP4 is non-empty and ffprobe reports a sane duration
  3. Output is viewable in any modern player

If this script lands on first run, the same filter graph idiom is safe to
paste into pipeline/compositor.py for the real per-beat render. If it
fails, we iterate here in 80 lines instead of in the production module.

Usage:
    python scripts/spike_filter_graph.py
    python scripts/spike_filter_graph.py --keep-pngs   # leave intermediates
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- shape parameters (match production where possible) ---------------------- #
WIDTH = 1920
HEIGHT = 1080
FPS = 25
SEG_SECONDS = 4.0  # each test segment ~4 s; production beats are 20-80 s
XFADE_SECONDS = 0.5  # mid-range of C-6.5 400-800 ms
ZOOM_END = 1.05  # Ken Burns: zoom from 1.0 -> 1.05 over the segment

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_MP4 = OUTPUT_DIR / "spike_output.mp4"

SRT_BODY = """\
1
00:00:00,500 --> 00:00:03,500
This is a calm caption on segment one.

2
00:00:04,000 --> 00:00:07,500
Mid clip caption that spans the
second crossfade gently.

3
00:00:08,000 --> 00:00:11,500
Final caption rests on the last card.
"""


def render_card(text: str, rgb: tuple[int, int, int], out_path: Path) -> Path:
    """Render a single 1920x1080 PNG with large centred text."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (WIDTH, HEIGHT), rgb)
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/segoeuib.ttf"
    try:
        font = ImageFont.truetype(font_path, size=120)
    except OSError:
        font = ImageFont.load_default()
    tw = draw.textlength(text, font=font)
    draw.text(((WIDTH - tw) / 2, HEIGHT / 2 - 60), text, fill=(245, 247, 250), font=font)
    img.save(out_path, "PNG")
    return out_path


def build_filter_graph(num_segments: int, srt_path: Path) -> str:
    """Build the -filter_complex string for N cards + xfade + subtitles.

    Strategy:
      [0:v] -> trim to SEG_SECONDS, apply zoompan -> [v0]
      [1:v] -> ditto -> [v1]
      ...
      xfade chains: [v0][v1] -> [x01], [x01][v2] -> [x012], ...
      finally subtitles= filter on the last xfade output -> [vout]
    """
    parts: list[str] = []
    # Per-segment zoompan + format. fps=FPS forces a constant rate the xfade
    # filter can align against.
    #
    # zoompan semantics gotcha: `d=N` means "emit N output frames PER INPUT
    # FRAME". With `-loop 1 -t SEG -framerate FPS` the demuxer hands zoompan
    # SEG*FPS input frames; we want one zoom step per input frame, so d=1.
    # The zoom expression progresses against `on` (the global output frame
    # counter) so the Ken Burns ramp covers the whole segment naturally.
    for i in range(num_segments):
        total_frames = int(SEG_SECONDS * FPS)
        inc = (ZOOM_END - 1.0) / total_frames
        zoom_expr = f"min(zoom+{inc:.6f},{ZOOM_END:.4f})"
        parts.append(
            f"[{i}:v]"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,"
            f"zoompan=z='{zoom_expr}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"format=yuv420p,fps={FPS},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

    # xfade chain. Offset is cumulative: segment k starts at
    #   k * SEG_SECONDS - k * XFADE_SECONDS
    # i.e. each crossfade eats XFADE_SECONDS off the previous segment.
    prev = "v0"
    for i in range(1, num_segments):
        offset = i * SEG_SECONDS - i * XFADE_SECONDS - XFADE_SECONDS
        label = f"x{i}"
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE_SECONDS}"
            f":offset={offset:.3f}[{label}]"
        )
        prev = label

    # subtitles burn-in on the final stream. Windows path escape per
    # pipeline.compositor convention.
    srt_arg = str(srt_path).replace("\\", "/").replace(":", r"\:")
    parts.append(
        f"[{prev}]subtitles='{srt_arg}':force_style="
        "'Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,"
        "BackColour=&HB2000000,BorderStyle=4,Outline=0,Shadow=0,"
        "Alignment=2,MarginV=70'[vout]"
    )
    return ";".join(parts)


def build_command(card_paths: list[Path], srt_path: Path, out_path: Path) -> list[str]:
    cmd: list[str] = ["ffmpeg", "-y", "-loglevel", "error"]
    for card in card_paths:
        cmd.extend(["-loop", "1", "-t", str(SEG_SECONDS), "-framerate", str(FPS), "-i", str(card)])
    filter_graph = build_filter_graph(len(card_paths), srt_path)
    cmd.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return cmd


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--keep-pngs", action="store_true", help="keep intermediate PNGs")
    args = p.parse_args(argv)

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: ffmpeg and ffprobe must be on PATH", file=sys.stderr)
        return 2

    workdir = Path(tempfile.mkdtemp(prefix="wl-spike-"))
    try:
        cards = [
            render_card("Segment One", (18, 22, 28), workdir / "card_0.png"),
            render_card("Segment Two", (28, 22, 32), workdir / "card_1.png"),
            render_card("Segment Three", (22, 30, 28), workdir / "card_2.png"),
        ]
        srt = workdir / "captions.srt"
        srt.write_text(SRT_BODY, encoding="utf-8")

        cmd = build_command(cards, srt, OUTPUT_MP4)
        print("=" * 78)
        print("ffmpeg command:")
        print(" ".join(cmd))
        print("=" * 78)

        subprocess.run(cmd, check=True)

        dur = probe_duration(OUTPUT_MP4)
        expected = len(cards) * SEG_SECONDS - (len(cards) - 1) * XFADE_SECONDS
        size_mb = OUTPUT_MP4.stat().st_size / 1024 / 1024
        print()
        print(f"OUTPUT:   {OUTPUT_MP4}")
        print(f"DURATION: {dur:.2f}s  (expected ~{expected:.2f}s)")
        print(f"SIZE:     {size_mb:.2f} MB")
        print()
        if abs(dur - expected) > 0.5:
            print("WARNING: duration drift > 0.5s; xfade offset math may be off")
            return 1
        print("SPIKE OK -- filter graph idiom validated.")
        return 0
    finally:
        if args.keep_pngs:
            print(f"intermediates preserved: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
