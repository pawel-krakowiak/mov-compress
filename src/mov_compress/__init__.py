"""mov-compress: a Textual TUI for compressing video files to a target size."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mov-compress")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
