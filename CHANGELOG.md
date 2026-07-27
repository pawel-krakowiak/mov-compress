# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for common video containers beyond `.mov`: `.mp4`, `.m4v`, `.mkv`,
  `.webm`, `.avi`, `.wmv`, `.flv`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.mts`,
  `.3gp` and `.ogv`. Containers that cannot carry H.264/AAC are written as MP4.
- Drag and drop: files dropped onto the terminal window are added to the queue.
- Command line interface: `mov-compress [files ...]` pre-fills the queue, and
  `--version` reports the installed version.
- A `justfile` with recipes for running, testing, linting and managing a shell
  alias (`just alias-install`, `alias-status`, `alias-uninstall`).
- CI running lint, format check and tests on Linux and macOS across Python
  3.11–3.13, plus a distribution build check.
- Tests for the app layer (driven headlessly through Textual), settings
  handling, and format selection.

### Changed

- The audio bitrate now scales down to at most a fifth of the bit budget instead
  of being fixed at 128 kbps, so small targets are no longer swallowed by the
  audio track.
- The status bar reports when the bitrate floors put an output over the
  requested target, instead of reporting plain success.

### Fixed

- A malformed, non-object or unwritable settings file no longer raises; the app
  falls back to defaults.
- Failures to spawn `ffmpeg`/`ffprobe`, and unparseable probe output, are now
  reported as a `CompressionError` rather than an unhandled exception.
- `python -m mov_compress` no longer launches the app as an import side effect.

## [0.1.0]

### Added

- Initial release: Textual TUI with a file queue, live two-pass encoding
  progress, a target size in MB, a persisted output directory, and settings that
  survive between runs.

[Unreleased]: https://github.com/pawel-krakowiak/mov-compress/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pawel-krakowiak/mov-compress/releases/tag/v0.1.0
