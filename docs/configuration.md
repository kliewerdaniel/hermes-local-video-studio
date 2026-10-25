# Configuration

## Nothing global

There is no config file and no required environment variable. Everything is
either discovered at run time or declared in the project specification. A
capability that depends on an undocumented shell setting is not reproducible.

## Paths

| what | where | override |
|---|---|---|
| ArtCraft binaries | `~/Projects/<app>/target/{release,debug}/<app>-cli` | `PATH` |
| Qwen studio | `http://127.0.0.1:8787` | `QwenAdapter(base=...)` |
| work directory | `<project-dir>/build` | `--workdir` |

`find_binary()` prefers a release build, falls back to a debug build, then
`PATH`. The fallback matters here: `photocraft` on this machine only has a debug
build, and a release-only lookup would report it missing.

## Project-level settings

```jsonc
"project": {
  "name": "lighthouse",
  "canvas": {"width": 1024, "height": 576},   // multiples of 32, always
  "fps": 24
},
"render": {"format": "h264", "bitrateKbps": 6000}
```

Canvas dimensions are the one setting constrained by the model rather than by
taste: Qwen-Image rejects anything that is not a positive multiple of 32. Exact
16:9 with 32-divisibility: 1024×576, 1536×864, 2048×1152.

## Bitrate, not quality

`bitrateKbps` is honoured. A quality-style setting is not — in testing, every
value across its range produced byte-identical files. If two exports differ in
nothing but a setting you changed, that setting was dropped; compare byte counts
before believing it applied.

## Motion

```jsonc
"motion": {"type": "push_in", "from": 100, "to": 112}
```

Scale is a percentage where 100 fits the canvas; `pull_out` runs the pair in
reverse. The runner passes **sequence-absolute** times to the NLE, because a
clip-relative time collapses the animation to a single keyframe with no error.
