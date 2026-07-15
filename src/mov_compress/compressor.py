"""Two-pass ffmpeg compression targeting a maximum output file size.

The target size is turned into a video bitrate budget: total bits available
(minus a safety margin and the audio track) divided by the clip duration.
Two-pass x264 encoding then distributes that budget across the whole clip,
which keeps the final file reliably at or under the requested size.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

OUTPUT_PREFIX = "c_"
AUDIO_BITRATE_KBPS = 128
MIN_VIDEO_BITRATE_KBPS = 100
SIZE_SAFETY_MARGIN = 0.97

ProgressCallback = Callable[[float], None]


class CompressionError(RuntimeError):
    """Raised when probing or encoding a video fails."""


@dataclass(frozen=True)
class VideoInfo:
    """Metadata needed to plan a compression job."""

    duration_s: float
    size_bytes: int
    has_audio: bool


def ffmpeg_available() -> bool:
    """Return True when both ffmpeg and ffprobe are on PATH."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(source: Path) -> VideoInfo:
    """Read duration, size and audio presence of a video via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CompressionError(f"ffprobe failed for {source.name}: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    duration_s = float(fmt.get("duration", 0.0))
    if duration_s <= 0:
        raise CompressionError(f"could not read duration of {source.name}")

    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    size_bytes = int(fmt.get("size", source.stat().st_size))
    return VideoInfo(duration_s=duration_s, size_bytes=size_bytes, has_audio=has_audio)


def video_bitrate_kbps(target_mb: float, duration_s: float, has_audio: bool) -> int:
    """Compute the video bitrate (kbps) that lands the output at the target size."""
    total_bits = target_mb * 1024 * 1024 * 8 * SIZE_SAFETY_MARGIN
    total_kbps = total_bits / duration_s / 1000
    audio_kbps = AUDIO_BITRATE_KBPS if has_audio else 0
    return max(int(total_kbps - audio_kbps), MIN_VIDEO_BITRATE_KBPS)


def plan_output_path(source: Path, output_dir: Path) -> Path:
    """Build a non-clobbering output path with the ``c_`` prefix."""
    candidate = output_dir / f"{OUTPUT_PREFIX}{source.name}"
    counter = 1
    while candidate.exists():
        candidate = output_dir / f"{OUTPUT_PREFIX}{source.stem}_{counter}{source.suffix}"
        counter += 1
    return candidate


def compress(
    source: Path,
    output_dir: Path,
    target_mb: float,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """Compress a video to at most ``target_mb`` megabytes and return the output path.

    Runs two encoding passes; ``on_progress`` receives a 0.0-1.0 fraction
    spanning both passes combined.
    """
    info = probe(source)
    bitrate = video_bitrate_kbps(target_mb, info.duration_s, info.has_audio)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = plan_output_path(source, output_dir)

    with tempfile.TemporaryDirectory(prefix="mov-compress-") as tmp:
        passlog = str(Path(tmp) / "ffmpeg2pass")
        common = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-loglevel", "error",
            "-progress", "pipe:1",
            "-y",
            "-i", str(source),
            "-c:v", "libx264",
            "-preset", "medium",
            "-b:v", f"{bitrate}k",
            "-maxrate", f"{bitrate}k",
            "-bufsize", f"{bitrate * 2}k",
            "-pix_fmt", "yuv420p",
            "-passlogfile", passlog,
        ]
        audio = ["-c:a", "aac", "-b:a", f"{AUDIO_BITRATE_KBPS}k"] if info.has_audio else ["-an"]
        pass_one = [*common, "-pass", "1", "-an", "-f", "null", os.devnull]
        pass_two = [*common, "-pass", "2", *audio, "-movflags", "+faststart", str(output)]

        try:
            _run_pass(pass_one, info.duration_s, base=0.0, span=0.5, on_progress=on_progress)
            _run_pass(pass_two, info.duration_s, base=0.5, span=0.5, on_progress=on_progress)
        except CompressionError:
            output.unlink(missing_ok=True)
            raise

    if on_progress is not None:
        on_progress(1.0)
    return output


def _run_pass(
    cmd: list[str],
    duration_s: float,
    base: float,
    span: float,
    on_progress: ProgressCallback | None,
) -> None:
    """Run one ffmpeg pass, mapping its progress into [base, base + span]."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    for line in process.stdout:
        key, _, value = line.strip().partition("=")
        if key == "out_time_us" and value.lstrip("-").isdigit():
            fraction = min(int(value) / 1_000_000 / duration_s, 1.0)
            if on_progress is not None:
                on_progress(base + fraction * span)

    _, stderr = process.communicate()
    if process.returncode != 0:
        detail = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown error"
        raise CompressionError(f"ffmpeg exited with code {process.returncode}: {detail}")
