"""Tests for input format acceptance and output container selection."""

from pathlib import Path

import pytest

from mov_compress.compressor import (
    FALLBACK_SUFFIX,
    FASTSTART_CONTAINERS,
    H264_CONTAINERS,
    INPUT_SUFFIXES,
    OUTPUT_PREFIX,
    output_suffix,
    plan_output_path,
)


@pytest.mark.parametrize("suffix", sorted(H264_CONTAINERS))
def test_h264_containers_keep_their_extension(suffix):
    assert output_suffix(Path(f"/videos/clip{suffix}")) == suffix


@pytest.mark.parametrize("suffix", [".webm", ".avi", ".wmv", ".mpg", ".mpeg", ".ogv"])
def test_other_containers_fall_back_to_mp4(suffix):
    assert output_suffix(Path(f"/videos/clip{suffix}")) == FALLBACK_SUFFIX


def test_output_suffix_is_case_insensitive():
    assert output_suffix(Path("/videos/CLIP.MOV")) == ".mov"


def test_every_h264_container_is_an_accepted_input():
    assert H264_CONTAINERS <= INPUT_SUFFIXES


def test_faststart_containers_are_a_subset_of_h264_containers():
    assert FASTSTART_CONTAINERS <= H264_CONTAINERS


def test_fallback_suffix_is_a_faststart_container():
    assert FALLBACK_SUFFIX in FASTSTART_CONTAINERS


def test_output_path_normalises_an_uppercase_extension(tmp_path: Path):
    output = plan_output_path(Path("/videos/CLIP.MOV"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}CLIP.mov"


def test_output_path_rewrites_an_unsupported_container(tmp_path: Path):
    output = plan_output_path(Path("/videos/clip.webm"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip.mp4"


def test_output_path_avoids_clobbering_after_a_rewrite(tmp_path: Path):
    (tmp_path / f"{OUTPUT_PREFIX}clip.mp4").touch()
    output = plan_output_path(Path("/videos/clip.avi"), tmp_path)
    assert output == tmp_path / f"{OUTPUT_PREFIX}clip_1.mp4"
