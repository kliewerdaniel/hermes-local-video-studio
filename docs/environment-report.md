# Environment report

Captured on the machine this system was built and tested on. Values are read from
the machine; nothing here is estimated.

## Host

| | |
|---|---|
| OS | Darwin 25.6.0 (26.6.2) |
| Architecture | arm64 |
| CPU | Apple M4 Pro, 14 cores |
| RAM | 51.5 GB |
| Python | 3.9.6 |
| Rust | cargo 1.87.0 (Homebrew) |
| Node | v22.23.1 |
| Git | git version 2.50.1 (Apple Git-155) |

## Media tooling

| | |
|---|---|
| ffmpeg | ffmpeg version 9.0.2 Copyright (c) 2000-2026 the FFmpeg developers |
| ffprobe | ffprobe version 9.0.2 Copyright (c) 2007-2026 the FFmpeg developers |
| text filters (`subtitles`/`ass`/`drawtext`) | **NO — absent from this build** |

The text-filter result is a real constraint, not a detail. This build cannot burn
a subtitle with any ffmpeg invocation, so captions must be composited as title
graphics. It was established by listing the filter catalogue
(`ffmpeg -hide_banner -filters`) and searching it, not by assuming a Homebrew
ffmpeg ships libass.

## ArtCraft suite

| app | binary | size |
|---|---|---|
| effectcraft | `~/Projects/effectcraft/target/release/effectcraft-cli` | 65.7 MB |
| filmcraft | `~/Projects/filmcraft/target/release/filmcraft-cli` | 33.7 MB |
| lightcraft | `~/Projects/lightcraft/target/release/lightcraft-cli` | 50.4 MB |
| photocraft | `~/Projects/photocraft/target/debug/photocraft-cli` | 57.8 MB |
| vectorcraft | `~/Projects/vectorcraft/target/release/vectorcraft-cli` | 44.8 MB |
| designcraft | `~/Projects/designcraft/target/release/designcraft-cli` | 36.1 MB |
| pdfcraft | `~/Projects/pdfcraft/target/release/pdfcraft-cli` | 30.7 MB |

All seven answer their `commands` catalogue, so they are probed capabilities
rather than files that merely exist. Note that `photocraft` is a **debug** build:
it runs, but its path differs from the others and a release-only lookup would
report it missing.

## Qwen-Image-2.1-Turbo

| | |
|---|---|
| studio path | `~/Projects/qwen-image-studio` |
| API | `http://127.0.0.1:8787` |
| weights | MLX Q8, ~17.8 GB, loaded on first generate |
| variants | one resident at a time (`loaded_variant`) |
| measured generation | see `docs/workflow.md` and the run manifest |

## Hermes

| | |
|---|---|
| version | Hermes Agent v0.22.2+1692.g22063fc (2026.9.24) · stable · local 22063fc099ec |
| skills directory | `~/.hermes/skills` |

## What was NOT verified

- Generation timings at resolutions other than those used in the recorded runs.
- Behaviour on Intel Macs or Linux: the MLX runtime is Apple-Silicon only.
- A fully clean install: this report describes an **existing** installation. The
  clean-install path in `installation.md` is marked where it is untested.
- The ArtCraft repository URLs, which are not published in this repo.
