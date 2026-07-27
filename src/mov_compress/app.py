"""Textual TUI for batch-compressing .mov files to a chosen maximum size."""

from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, DirectoryTree, Footer, Header, Input, Label

from .compressor import CompressionError, compress, ffmpeg_available
from .config import Settings

MOV_SUFFIXES = {".mov"}
PROGRESS_BAR_WIDTH = 20

STATUS_LABELS = {
    "queued": "queued",
    "running": "running",
    "done": "done",
    "failed": "failed",
    "skipped": "skipped (under target)",
}


@dataclass
class Job:
    """One file in the compression queue."""

    source: Path
    status: str = "queued"
    progress: float = 0.0
    output: Path | None = None
    error: str = ""


class JobProgress(Message):
    """Progress update for a running job, posted from the worker thread."""

    def __init__(self, index: int, fraction: float) -> None:
        self.index = index
        self.fraction = fraction
        super().__init__()


class JobStatus(Message):
    """Status change of a job, posted from the worker thread."""

    def __init__(
        self,
        index: int,
        status: str,
        output: Path | None = None,
        error: str = "",
    ) -> None:
        self.index = index
        self.status = status
        self.output = output
        self.error = error
        super().__init__()


class MovTree(DirectoryTree):
    """Directory tree that only shows directories and .mov files."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [
            path
            for path in paths
            if (path.is_dir() and not path.name.startswith("."))
            or path.suffix.lower() in MOV_SUFFIXES
        ]


def parse_dropped_paths(text: str) -> list[Path]:
    """Extract existing .mov files from text a terminal produces on file drop.

    macOS terminals paste the dragged file's path shell-escaped (spaces as
    ``\\ ``, or the whole path quoted), separating multiple files with spaces,
    which :func:`shlex.split` unescapes for us.
    """
    text = text.strip()
    if not text:
        return []
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = [text]
    paths = []
    for token in tokens:
        if token.startswith("file://"):
            token = token[len("file://") :]
        path = Path(token).expanduser()
        if path.suffix.lower() in MOV_SUFFIXES and path.is_file():
            paths.append(path)
    return paths


class DropInput(Input):
    """Input that queues dropped .mov files instead of typing their paths."""

    def _on_paste(self, event: events.Paste) -> None:
        if parse_dropped_paths(event.text):
            event.stop()
            self.app.enqueue_dropped(event.text)
            return
        super()._on_paste(event)


def reveal_in_file_manager(path: Path) -> None:
    """Open the platform file manager with the given file highlighted."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def human_size(size_bytes: int) -> str:
    """Format a byte count as a short human-readable string."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def progress_bar(fraction: float) -> str:
    """Render a text progress bar for a 0.0-1.0 fraction."""
    filled = round(fraction * PROGRESS_BAR_WIDTH)
    bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)
    return f"{bar} {fraction:4.0%}"


@dataclass
class QueueState:
    """Jobs added by the user, in the order they were added."""

    jobs: list[Job] = field(default_factory=list)

    def contains(self, source: Path) -> bool:
        return any(job.source == source for job in self.jobs)


class MovCompressApp(App):
    """Batch .mov compressor with a fixed output directory and size target."""

    TITLE = "mov-compress"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("c", "compress", "Compress"),
        ("o", "open_location", "Open location"),
        ("r", "remove_job", "Remove"),
        ("x", "clear_queue", "Clear"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.queue = QueueState()

    def compose(self) -> ComposeResult:
        browse_root = Path(self.settings.browse_dir or Path.home())
        if not browse_root.is_dir():
            browse_root = Path.home()

        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="browser"):
                yield Label("Pick .mov files", classes="panel-title")
                yield Label("or drag one onto the terminal", classes="panel-hint")
                yield MovTree(browse_root, id="tree")
            with Vertical(id="main"):
                with Horizontal(id="options"):
                    with Vertical(classes="option"):
                        yield Label("Max size (MB)")
                        yield DropInput(str(self.settings.target_mb), id="target-mb")
                    with Vertical(classes="option option-wide"):
                        yield Label("Output directory (empty = next to source)")
                        yield DropInput(
                            self.settings.output_dir,
                            placeholder=str(Path.home() / "Movies" / "compressed"),
                            id="output-dir",
                        )
                yield DataTable(id="queue")
                with Horizontal(id="actions"):
                    yield Button("Compress", variant="primary", id="compress")
                    yield Button("Open location", id="open-location")
                    yield Button("Remove", id="remove")
                    yield Button("Clear", id="clear")
                yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#queue", DataTable)
        table.cursor_type = "row"
        table.add_column("File", key="file")
        table.add_column("Size", key="size")
        table.add_column("Status", key="status")
        table.add_column("Progress", key="progress")
        if not ffmpeg_available():
            self.notify(
                "ffmpeg/ffprobe not found on PATH. Install it first (brew install ffmpeg).",
                severity="error",
                timeout=30,
            )

    # --- queue management -------------------------------------------------

    @on(DirectoryTree.FileSelected, "#tree")
    def add_file(self, event: DirectoryTree.FileSelected) -> None:
        if self.enqueue_source(event.path):
            self.set_status(f"queued {event.path.name}")

    def enqueue_source(self, source: Path) -> bool:
        """Add one .mov file to the queue. Returns True if it was added."""
        if source.suffix.lower() not in MOV_SUFFIXES:
            return False
        if self.queue.contains(source):
            self.set_status(f"{source.name} is already queued")
            return False

        job = Job(source=source)
        self.queue.jobs.append(job)
        table = self.query_one("#queue", DataTable)
        table.add_row(
            source.name,
            human_size(source.stat().st_size),
            STATUS_LABELS[job.status],
            progress_bar(0.0),
            key=str(len(self.queue.jobs) - 1),
        )
        self.settings.browse_dir = str(source.parent)
        return True

    def enqueue_dropped(self, text: str) -> None:
        """Queue any .mov files found in text dropped onto the terminal."""
        added = [path for path in parse_dropped_paths(text) if self.enqueue_source(path)]
        if len(added) == 1:
            self.set_status(f"queued {added[0].name}")
        elif added:
            self.set_status(f"queued {len(added)} files")

    def on_paste(self, event: events.Paste) -> None:
        """Handle a file dropped onto the terminal while the queue has focus."""
        if parse_dropped_paths(event.text):
            event.stop()
            self.enqueue_dropped(event.text)

    def action_remove_job(self) -> None:
        job, index = self.selected_job()
        if job is None or index is None:
            return
        if job.status == "running":
            self.set_status("cannot remove a running job")
            return
        self.queue.jobs.pop(index)
        self.rebuild_table()

    def action_clear_queue(self) -> None:
        if any(job.status == "running" for job in self.queue.jobs):
            self.set_status("cannot clear while compression is running")
            return
        self.queue.jobs.clear()
        self.rebuild_table()
        self.set_status("queue cleared")

    def rebuild_table(self) -> None:
        table = self.query_one("#queue", DataTable)
        table.clear()
        for index, job in enumerate(self.queue.jobs):
            table.add_row(
                job.source.name,
                human_size(job.source.stat().st_size),
                STATUS_LABELS.get(job.status, job.status),
                progress_bar(job.progress),
                key=str(index),
            )

    def selected_job(self) -> tuple[Job | None, int | None]:
        """Return the job under the table cursor, if any."""
        table = self.query_one("#queue", DataTable)
        if not self.queue.jobs or table.cursor_row is None or table.cursor_row < 0:
            return None, None
        row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
        if row_key is None:
            return None, None
        index = int(row_key)
        return self.queue.jobs[index], index

    # --- compression ------------------------------------------------------

    @on(Button.Pressed, "#compress")
    def action_compress(self) -> None:
        if not ffmpeg_available():
            self.notify("ffmpeg is not installed", severity="error")
            return

        target_mb = self.parse_target_mb()
        if target_mb is None:
            return
        output_dir = self.parse_output_dir()
        if output_dir is None:
            return

        pending = [
            (index, job)
            for index, job in enumerate(self.queue.jobs)
            if job.status in ("queued", "failed")
        ]
        if not pending:
            self.set_status("nothing to compress - add some .mov files first")
            return

        self.settings.target_mb = target_mb
        self.settings.output_dir = str(output_dir) if output_dir != Path() else ""
        self.settings.save()
        self.run_jobs(pending, target_mb, output_dir)

    def parse_target_mb(self) -> float | None:
        raw = self.query_one("#target-mb", Input).value.strip().replace(",", ".")
        try:
            target_mb = float(raw)
        except ValueError:
            target_mb = 0.0
        if target_mb <= 0:
            self.notify("Max size must be a positive number of megabytes", severity="error")
            return None
        return target_mb

    def parse_output_dir(self) -> Path | None:
        """Return the fixed output directory, or ``Path()`` for next-to-source."""
        raw = self.query_one("#output-dir", Input).value.strip()
        if not raw:
            return Path()
        output_dir = Path(raw).expanduser()
        if output_dir.exists() and not output_dir.is_dir():
            self.notify(f"{output_dir} exists and is not a directory", severity="error")
            return None
        return output_dir

    @work(thread=True, exclusive=True)
    def run_jobs(
        self,
        pending: list[tuple[int, Job]],
        target_mb: float,
        output_dir: Path,
    ) -> None:
        """Compress queued jobs one by one on a worker thread."""
        target_bytes = target_mb * 1024 * 1024
        for index, job in pending:
            if job.source.stat().st_size <= target_bytes:
                self.post_message(JobStatus(index, "skipped"))
                continue

            self.post_message(JobStatus(index, "running"))
            destination = output_dir if output_dir != Path() else job.source.parent
            try:
                output = compress(
                    job.source,
                    destination,
                    target_mb,
                    on_progress=lambda f, i=index: self.post_message(JobProgress(i, f)),
                )
            except CompressionError as error:
                self.post_message(JobStatus(index, "failed", error=str(error)))
            else:
                self.post_message(JobStatus(index, "done", output=output))

    def on_job_progress(self, message: JobProgress) -> None:
        job = self.queue.jobs[message.index]
        job.progress = message.fraction
        table = self.query_one("#queue", DataTable)
        table.update_cell(str(message.index), "progress", progress_bar(message.fraction))

    def on_job_status(self, message: JobStatus) -> None:
        job = self.queue.jobs[message.index]
        job.status = message.status
        job.output = message.output
        job.error = message.error
        table = self.query_one("#queue", DataTable)
        table.update_cell(str(message.index), "status", STATUS_LABELS[message.status])

        if message.status == "done" and message.output is not None:
            job.progress = 1.0
            table.update_cell(str(message.index), "progress", progress_bar(1.0))
            size = human_size(message.output.stat().st_size)
            self.set_status(f"saved {message.output.name} ({size})")
        elif message.status == "failed":
            self.set_status(f"{job.source.name} failed: {message.error}")
        elif message.status == "skipped":
            self.set_status(f"{job.source.name} is already under the target size")

    # --- helpers ----------------------------------------------------------

    @on(Button.Pressed, "#open-location")
    def action_open_location(self) -> None:
        job, _ = self.selected_job()
        if job is None:
            self.set_status("select a file in the queue first")
            return
        target = job.output if job.output is not None else job.source
        reveal_in_file_manager(target)

    @on(Button.Pressed, "#remove")
    def on_remove_pressed(self) -> None:
        self.action_remove_job()

    @on(Button.Pressed, "#clear")
    def on_clear_pressed(self) -> None:
        self.action_clear_queue()

    def set_status(self, text: str) -> None:
        self.query_one("#status", Label).update(text)

    def action_quit(self) -> None:
        self.settings.save()
        self.exit()


def main() -> None:
    """Entry point for the ``mov-compress`` command."""
    MovCompressApp().run()


if __name__ == "__main__":
    main()
