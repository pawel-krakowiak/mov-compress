# mov-compress

A terminal UI for batch-compressing video files down to a chosen maximum size
(e.g. "make these fit in 30 MB"), built with [Textual](https://textual.textualize.io/)
and powered by two-pass `ffmpeg` encoding.

[![CI](https://github.com/pawel-krakowiak/mov-compress/actions/workflows/ci.yml/badge.svg)](https://github.com/pawel-krakowiak/mov-compress/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

You give it a size, not a bitrate. It works out how many bits fit in that budget,
spends them across the whole clip with two-pass x264, and lands the output at or
under what you asked for.

## Features

- **Target size, not bitrate** - enter a max size in MB; the bitrate is computed
  from the clip duration so the output reliably lands at or under the target
- **Multi-file queue** - browse the filesystem in-app and queue any number of files
- **Many formats** - `.mov`, `.mp4`, `.mkv`, `.webm`, `.avi` and more (see below)
- **Drag & drop** - drag files onto the terminal window to queue them instantly
  (macOS Terminal.app and iTerm2)
- **Two-pass x264** - the bit budget is spread over the whole clip for the best
  quality achievable at that size
- **Live progress** - a per-file progress bar spanning both encoding passes
- **Open location** - reveal the compressed file in Finder/Explorer with one key
- **Fixed output directory** - optionally save every output to one folder
  (persisted between runs); otherwise files are saved next to the source
- Outputs are prefixed with `c_` (`clip.mov` → `c_clip.mov`) and never overwrite
  existing files
- Files already under the target size are skipped

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) with `ffprobe` on `PATH`, built with `libx264`

```sh
brew install ffmpeg        # macOS
sudo apt install ffmpeg    # Debian/Ubuntu
winget install ffmpeg      # Windows
```

## Install

```sh
git clone https://github.com/pawel-krakowiak/mov-compress.git
cd mov-compress
just install
```

No [just](https://github.com/casey/just)? Every recipe is a one-liner -
`just install` is simply `uv sync`.

## Usage

```sh
just run                       # launch the TUI
just run clip.mov other.mp4    # launch with files already queued
```

Or, without `just`:

```sh
uv run mov-compress
uv run mov-compress clip.mov
```

### A shorter command

To run it from anywhere, either install it as a global tool:

```sh
just install-tool     # uv tool install .
mov-compress
```

...or add a shell alias pointing back at this checkout:

```sh
just alias-show       # print the alias, change nothing
just alias-install    # add it to your shell startup file
just alias-status     # check whether it is installed
just alias-uninstall  # remove it again
```

`alias-install` detects your shell (zsh, bash, fish, or `~/.profile`), backs the
file up before writing, refuses to clobber an existing `mc` alias, and verifies
the line landed. Then:

```sh
source ~/.zshrc   # or open a new terminal
mc                # launches mov-compress
mc clip.mov       # ...with a file already queued
```

Pick a different name with `just alias_name=movc alias-install`.

### Key bindings

| Key | Action |
| --- | --- |
| `c` | Compress the queue |
| `o` | Open the location of the selected (compressed) file |
| `r` | Remove the selected file from the queue |
| `x` | Clear the queue |
| `q` | Quit |

## Supported formats

Input: `.mov` `.mp4` `.m4v` `.mkv` `.webm` `.avi` `.wmv` `.flv` `.mpg` `.mpeg`
`.ts` `.m2ts` `.mts` `.3gp` `.ogv`

Output is always H.264 video with AAC audio. The source container is kept when it
can carry those streams; formats that cannot (`.webm`, `.avi`, `.wmv`, `.mpg`,
`.mpeg`, `.ogv`) are written as `.mp4` instead. So `clip.webm` becomes `c_clip.mp4`,
while `clip.mkv` stays `c_clip.mkv`.

## How it works

The target size becomes a total bit budget (with a 3% safety margin). Audio takes
up to 128 kbps - but never more than a fifth of the budget, so a small target is
not swallowed by the audio track - and the remainder goes to video:

```
total_kbps = target_MB * 8 * 1024^2 * 0.97 / duration_s / 1000
audio_kbps = clamp(total_kbps * 0.2, 48, 128)
video_kbps = total_kbps - audio_kbps
```

`ffmpeg` then runs two x264 passes at that bitrate, so the encoder sees the whole
clip in advance and puts the bits where they matter most.

**A caveat on very small targets.** Video never drops below 100 kbps and audio
never below 48 kbps, because output below that is not worth having. A long clip
squeezed into a tiny target therefore lands *over* it - the app says so in the
status bar rather than pretending it succeeded.

Settings (target size, output directory, last browsed folder) live in the platform
config directory, e.g. `~/Library/Application Support/mov-compress/config.json`
on macOS.

## Development

```sh
just            # list every recipe
just check      # lint, format check and tests - what CI runs
just test       # tests only
just fmt        # auto-fix and format
just clean      # remove caches and build artefacts
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## License

[MIT](LICENSE)
