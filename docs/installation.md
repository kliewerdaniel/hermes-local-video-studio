# Installation

Two paths: integrate with an existing setup, or build from clean. Every command
below was run on the machine described in `environment-report.md` unless marked
**untested**.

## A. Prerequisites

| requirement | why | check |
|---|---|---|
| macOS on Apple Silicon | MLX inference | `uname -m` → `arm64` |
| Python ≥ 3.9 | the package | `python3 --version` |
| ffmpeg + ffprobe | measurement and muxing | `ffmpeg -version` |
| ~20 GB free disk | Qwen Q8 weights are ~17.8 GB | `df -h ~` |
| ≥ 48 GB RAM recommended | one 17.8 GB variant resident, plus headroom | `sysctl hw.memsize` |

On 32 GB the model will load but a batch has almost no headroom; expect OOM
kills when anything else large runs.

## B. Integrate with an existing installation

If the ArtCraft suite and the Qwen studio are already installed:

```bash
git clone https://github.com/kliewerdaniel/hermes-local-video-studio ~/Projects/hermes-local-video-studio
cd ~/Projects/hermes-local-video-studio
scripts/setup
scripts/doctor
```

`scripts/doctor` discovers the tools; it does not install them. Expected output
is one line per app with a path, and `qwen: reachable` once the studio is up.

## C. Clean installation

**1. Developer tools**

```bash
xcode-select --install          # if not already present
```

**2. Homebrew packages**

```bash
brew install ffmpeg python@3.12
```

**3. Rust toolchain** (needed to build the ArtCraft apps)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**4. The ArtCraft apps** — one repository each, built release:

```bash
for app in effectcraft filmcraft lightcraft photocraft vectorcraft designcraft pdfcraft; do
  git clone <app-repo> ~/Projects/$app
  ( cd ~/Projects/$app && cargo build --release -p ${app}-cli )
done
```

**untested**: the repository URLs for the ArtCraft apps are not published in this
repo. If you do not have them, `doctor` will report `missing` and the stages that
need them will be skipped rather than faked.

**5. Qwen-Image-2.1-Turbo studio**

```bash
git clone <qwen-studio-repo> ~/Projects/qwen-image-studio
cd ~/Projects/qwen-image-studio
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./start.sh                       # downloads the Q8 MLX weights on first run
```

Weights are fetched on demand and are **not** part of this repository.

**6. This repository**

```bash
git clone https://github.com/kliewerdaniel/hermes-local-video-studio ~/Projects/hermes-local-video-studio
cd ~/Projects/hermes-local-video-studio
python3 -m pip install -e ".[measure]"
scripts/doctor
```

`numpy` and `pillow` are only needed for the *measurement* helpers (frame diffs,
luma structure). Without them, schema validation and the NLE adapter still work;
the motion and content checks report as skipped rather than passing.

## D. Smoke test (no model required)

```bash
scripts/smoke
```

Runs the unit and integration tests, validates the example project, and prints the
capability summary. This is the fastest way to know the install is sane.

## E. First production

```bash
cd ~/Projects/qwen-image-studio && ./start.sh     # terminal 1
cd ~/Projects/hermes-local-video-studio
scripts/run-project examples/minimal-project/project.json
```

Expected: three asset steps, three place steps, two motion steps, two transition
steps, a render, and four verification steps. Total ~10–15 minutes on an M4 Pro,
dominated by image generation.

## Removal

```bash
python3 -m pip uninstall hermes-local-video-studio
rm -rf ~/Projects/hermes-local-video-studio
```

Nothing outside the repo and the python environment is modified. Model weights
live in the Qwen studio's own directory and are removed with it.
