"""Headless tests driving the Textual app itself."""

import asyncio
from pathlib import Path

import pytest

from mov_compress import config
from mov_compress.app import MovCompressApp, human_size, progress_bar


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep the tests away from the real user config file."""
    monkeypatch.setattr(config, "config_file", lambda: tmp_path / "config.json")


def make_clip(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_bytes(b"\x00" * 2048)
    return path


def run_app(app: MovCompressApp, body) -> None:
    """Boot ``app`` headless and run the async ``body`` against it."""

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await body(pilot)

    asyncio.run(scenario())


def test_files_from_the_command_line_are_queued(tmp_path):
    clip = make_clip(tmp_path, "clip.mov")
    app = MovCompressApp(initial_files=[clip])

    async def body(pilot):
        assert [job.source for job in app.queue.jobs] == [clip]

    run_app(app, body)


def test_mixed_formats_are_all_queued(tmp_path):
    clips = [make_clip(tmp_path, f"clip.{ext}") for ext in ("mov", "mp4", "mkv", "webm", "avi")]
    app = MovCompressApp(initial_files=clips)

    async def body(pilot):
        assert [job.source for job in app.queue.jobs] == clips

    run_app(app, body)


def test_unsupported_and_missing_files_are_rejected(tmp_path):
    note = tmp_path / "notes.txt"
    note.write_text("x")
    app = MovCompressApp(initial_files=[note, tmp_path / "ghost.mov"])

    async def body(pilot):
        assert app.queue.jobs == []

    run_app(app, body)


def test_the_same_file_is_never_queued_twice(tmp_path):
    clip = make_clip(tmp_path, "clip.mov")
    app = MovCompressApp()

    async def body(pilot):
        assert app.enqueue_source(clip) is True
        assert app.enqueue_source(clip) is False
        assert len(app.queue.jobs) == 1

    run_app(app, body)


def test_clearing_the_queue_empties_the_table(tmp_path):
    clips = [make_clip(tmp_path, "a.mov"), make_clip(tmp_path, "b.mp4")]
    app = MovCompressApp(initial_files=clips)

    async def body(pilot):
        assert len(app.queue.jobs) == 2
        await pilot.press("x")
        assert app.queue.jobs == []

    run_app(app, body)


def test_a_rejected_target_size_does_not_start_a_run(tmp_path):
    app = MovCompressApp(initial_files=[make_clip(tmp_path, "clip.mov")])

    async def body(pilot):
        app.query_one("#target-mb").value = "not a number"
        assert app.parse_target_mb() is None

    run_app(app, body)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("30", 30.0), ("2,5", 2.5), (" 7.5 ", 7.5)],
)
def test_target_size_accepts_comma_and_whitespace(tmp_path, raw, expected):
    app = MovCompressApp()

    async def body(pilot):
        app.query_one("#target-mb").value = raw
        assert app.parse_target_mb() == expected

    run_app(app, body)


def test_human_size_formats_each_unit():
    assert human_size(512) == "512.0 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_progress_bar_spans_empty_to_full():
    assert progress_bar(0.0).endswith("  0%")
    assert progress_bar(1.0).endswith("100%")
    assert "█" not in progress_bar(0.0)
    assert "░" not in progress_bar(1.0)
