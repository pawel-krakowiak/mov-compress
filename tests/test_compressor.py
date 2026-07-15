"""Unit tests for the size-budget math and output path planning."""

from pathlib import Path

from mov_compress.compressor import (
    AUDIO_BITRATE_KBPS,
    MIN_VIDEO_BITRATE_KBPS,
    OUTPUT_PREFIX,
    SIZE_SAFETY_MARGIN,
    plan_output_path,
    video_bitrate_kbps,
)


def test_bitrate_fits_target_size():
    target_mb, duration_s = 30.0, 60.0
    bitrate = video_bitrate_kbps(target_mb, duration_s, has_audio=True)
    total_bits = (bitrate + AUDIO_BITRATE_KBPS) * 1000 * duration_s
    assert total_bits <= target_mb * 1024 * 1024 * 8


def test_bitrate_uses_safety_margin():
    bitrate = video_bitrate_kbps(30.0, 60.0, has_audio=False)
    expected = int(30.0 * 1024 * 1024 * 8 * SIZE_SAFETY_MARGIN / 60.0 / 1000)
    assert bitrate == expected


def test_bitrate_reserves_audio_budget():
    with_audio = video_bitrate_kbps(30.0, 60.0, has_audio=True)
    without_audio = video_bitrate_kbps(30.0, 60.0, has_audio=False)
    assert without_audio - with_audio == AUDIO_BITRATE_KBPS


def test_bitrate_never_drops_below_minimum():
    bitrate = video_bitrate_kbps(1.0, 3600.0, has_audio=True)
    assert bitrate == MIN_VIDEO_BITRATE_KBPS


def test_output_path_gets_prefix(tmp_path: Path):
    output = plan_output_path(Path("/videos/clip.mov"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip.mov"


def test_output_path_avoids_clobbering(tmp_path: Path):
    (tmp_path / f"{OUTPUT_PREFIX}clip.mov").touch()
    (tmp_path / f"{OUTPUT_PREFIX}clip_1.mov").touch()
    output = plan_output_path(Path("/videos/clip.mov"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip_2.mov"
