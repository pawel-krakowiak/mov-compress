"""Tests for parsing file paths dropped onto the terminal."""

from pathlib import Path

from mov_compress.app import parse_dropped_paths


def _make_mov(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_bytes(b"\x00")
    return path


def test_parses_backslash_escaped_path_with_trailing_space(tmp_path):
    clip = _make_mov(tmp_path, "my clip.mov")
    dropped = f"{tmp_path}/my\\ clip.mov "
    assert parse_dropped_paths(dropped) == [clip]


def test_parses_quoted_path(tmp_path):
    clip = _make_mov(tmp_path, "my clip.mov")
    assert parse_dropped_paths(f"'{tmp_path}/my clip.mov'") == [clip]


def test_parses_multiple_dropped_files(tmp_path):
    first = _make_mov(tmp_path, "a.mov")
    second = _make_mov(tmp_path, "b.mov")
    dropped = f"{first} {second}"
    assert parse_dropped_paths(dropped) == [first, second]


def test_strips_file_uri_scheme(tmp_path):
    clip = _make_mov(tmp_path, "a.mov")
    assert parse_dropped_paths(f"file://{clip}") == [clip]


def test_ignores_non_mov_and_missing_files(tmp_path):
    (tmp_path / "notes.txt").write_bytes(b"x")
    dropped = f"{tmp_path}/notes.txt {tmp_path}/ghost.mov"
    assert parse_dropped_paths(dropped) == []


def test_empty_input_returns_empty_list():
    assert parse_dropped_paths("   ") == []
