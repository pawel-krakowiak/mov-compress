# mov-compress

A terminal UI for batch-compressing `.mov` files down to a chosen maximum size
(e.g. "make these fit in 30 MB"), built with [Textual](https://textual.textualize.io/)
and powered by two-pass `ffmpeg` encoding.

![status](https://img.shields.io/badge/status-personal_tool-blue)

## Features

- **Multi-file queue** - browse the filesystem in-app and pick any number of `.mov` files
- **Target size, not bitrate** - enter a max size in MB; the video bitrate is computed
  from the clip duration so the output reliably lands at or under the target
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
- [ffmpeg](https://ffmpeg.org/) with `ffprobe` on `PATH` (`brew install ffmpeg`)

## Usage

Run straight from the repo:

```sh
uv run mov-compress
```

Or install it as a tool available everywhere:

```sh
uv tool install .
mov-compress
```

### Key bindings

| Key | Action |
| --- | --- |
| `c` | Compress the queue |
| `o` | Open the location of the selected (compressed) file |
| `r` | Remove the selected file from the queue |
| `x` | Clear the queue |
| `q` | Quit |

## How it works

For each file the target size is converted into a total bit budget
(with a 3% safety margin), the audio track gets a fixed 128 kbps AAC slice,
and the remainder becomes the video bitrate:

```
video_kbps = target_MB * 8 * 1024^2 * 0.97 / duration_s / 1000 - 128
```

`ffmpeg` then runs two x264 passes with that bitrate, so the encoder knows the
whole clip in advance and distributes bits where they matter most.

Settings (target size, output directory, last browsed folder) are stored in the
platform config directory, e.g. `~/Library/Application Support/mov-compress/config.json`
on macOS.

## Development

```sh
uv sync            # install dependencies
uv run pytest      # run tests
uv run ruff check  # lint
```

## License

[MIT](LICENSE)
