# Contributing

Thanks for taking a look. This is a small personal tool, but issues and pull
requests are welcome.

## Getting set up

You need [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just)
and [ffmpeg](https://ffmpeg.org/) (with `libx264`).

```sh
git clone https://github.com/pawel-krakowiak/mov-compress.git
cd mov-compress
just install
just check
```

`just` is a convenience, not a requirement — run `just --list` to see the plain
command behind each recipe.

## Before opening a pull request

```sh
just check    # ruff check, ruff format --check, pytest
```

CI runs exactly this on Linux and macOS across Python 3.11–3.13, so a green
`just check` locally should mean a green pipeline.

The tests are fast because none of them shell out to ffmpeg — they cover the
bitrate maths, output path planning, drag-and-drop parsing, settings handling,
and the TUI driven headlessly through Textual's `run_test()`. If you change how
encoding is invoked, please also try it against a real file.

## Style

- Ruff is the only formatter and linter; `just fmt` fixes what it can.
- Line length is 100.
- Public functions carry a one-line docstring explaining *why*, not *what*.
- Type annotations everywhere, with `from __future__ import annotations`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
`docs:`, `test:`, `refactor:`, `chore:`, `ci:`, `build:`, with an optional scope
such as `feat(tui):`. Keep the subject line short and in the imperative mood.

## Adding support for another format

Input formats live in `INPUT_SUFFIXES` in `src/mov_compress/compressor.py`. If
the container can carry H.264 video and AAC audio, add it to `H264_CONTAINERS`
too, so the output keeps the source extension; otherwise it is written as MP4
automatically. `FASTSTART_CONTAINERS` lists the MP4-family containers that accept
`-movflags +faststart`. The tests in `tests/test_formats.py` assert these sets
stay consistent with one another.
