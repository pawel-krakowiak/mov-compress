"""Unit tests for the size-budget math and output path planning."""

from pathlib import Path

from mov_compress.compressor import (
    AUDIO_BITRATE_KBPS,
    MIN_AUDIO_BITRATE_KBPS,
    MIN_VIDEO_BITRATE_KBPS,
    OUTPUT_PREFIX,
    SIZE_SAFETY_MARGIN,
    audio_bitrate_kbps,
    plan_output_path,
    total_bitrate_kbps,
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


def test_audio_gets_the_full_rate_when_the_budget_is_roomy():
    assert audio_bitrate_kbps(30.0, 60.0, has_audio=True) == AUDIO_BITRATE_KBPS


def test_audio_is_silent_without_an_audio_track():
    assert audio_bitrate_kbps(30.0, 60.0, has_audio=False) == 0


def test_audio_shrinks_to_its_share_of_a_tight_budget():
    # 1 MB over 30 s leaves ~271 kbps in total; audio may take a fifth of it.
    total = total_bitrate_kbps(1.0, 30.0)
    assert audio_bitrate_kbps(1.0, 30.0, has_audio=True) == int(total * 0.2)


def test_audio_never_drops_below_its_minimum():
    assert audio_bitrate_kbps(0.5, 3600.0, has_audio=True) == MIN_AUDIO_BITRATE_KBPS


def test_tight_budget_still_fits_the_target():
    target_mb, duration_s = 1.0, 30.0
    video = video_bitrate_kbps(target_mb, duration_s, has_audio=True)
    audio = audio_bitrate_kbps(target_mb, duration_s, has_audio=True)
    total_bits = (video + audio) * 1000 * duration_s
    assert total_bits <= target_mb * 1024 * 1024 * 8


def test_output_path_gets_prefix(tmp_path: Path):
    output = plan_output_path(Path("/videos/clip.mov"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip.mov"


def test_output_path_avoids_clobbering(tmp_path: Path):
    (tmp_path / f"{OUTPUT_PREFIX}clip.mov").touch()
    (tmp_path / f"{OUTPUT_PREFIX}clip_1.mov").touch()
    output = plan_output_path(Path("/videos/clip.mov"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip_2.mov"
