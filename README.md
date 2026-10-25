# hermes-local-video-studio

A reproducible local video-production capability for Hermes agents: **Qwen-Image-2.1-Turbo**
for stills, the **ArtCraft Rust suite** for compositing and editing, and a validation
layer that refuses to call anything done that it has not measured.

No cloud. No GUI. No API keys.

## The rule this repository is built on

> An operation is not done because a command returned `0`. It is done when
> something measured the result.

Every step is recorded as **verified** (a measurement is attached) or
**requested_only** (the tool accepted the command; nothing checked it). A run
that reports `failed: 0` alongside several `requested_only` steps is a partial
success, and it says so.

That distinction is not pedantry. In building this, four separate failures
returned success: a dissolve that never applied, a keyframe that animated
nothing, a JSON parser that silently returned a fragment, and an NLE that
normalised audio into clipping. Each was caught by measuring, not by reading an
exit code.

## Quick start

```bash
# 1. is the machine able?
scripts/doctor

# 2. does the code work? (no model needed)
scripts/smoke

# 3. produce a film
cd ~/Projects/qwen-image-studio && ./start.sh        # terminal 1
cd ~/Projects/hermes-local-video-studio
scripts/run-project examples/minimal-project/project.json
```

Expected: 17 verified steps, 0 failed, a 12.01 s h264 film at 1024×576.

## What it does

```
brief -> project.json -> validate -> probe -> generate -> assemble -> render -> verify
                                                                              |
                                                                     manifest.json
```

| stage | module | refuses to |
|---|---|---|
| validate | `hlvs/schema.py` | accept unknown ops, bad dimensions, dangling refs |
| probe | `hlvs/capabilities.py` | claim a tool works because a path exists |
| generate | `hlvs/adapters/qwen.py` | return before `result.path` exists |
| assemble | `hlvs/adapters/filmcraft.py` | let item ids pass as clip ids |
| render | `hlvs/adapters/filmcraft.py` | export when the dissolve count is wrong |
| verify | `hlvs/adapters/media.py` | trust any renderer's own report |

## Layout

```
hlvs/            the package (stdlib only; numpy/pillow optional for measurement)
  schema.py      project validation + allowlists
  capabilities.py  doctor: what exists AND what answers
  provenance.py  StepResult, manifests, hashes
  runner.py      ordering, resume, fatal-on-silent-failure
  adapters/      qwen | filmcraft | media
schemas/         JSON Schema copy for editors
skills/          9 installable Hermes skills
scripts/         doctor, setup, smoke, validate-project, run-project, verify-output
examples/        minimal-project (3 scenes, 2 dissolves, 2 motions)
tests/           unit (schema, provenance) + integration (real ffmpeg)
docs/            architecture, installation, configuration, workflow,
                 troubleshooting, verification, security, environment report
docs/evidence/   manifest + capability report + a real frame from a real run
```

## The project format

```jsonc
{
  "schema_version": "1.0",
  "project": {"name": "lighthouse", "canvas": {"width": 1024, "height": 576}, "fps": 24},
  "assets":  [{"id": "a1", "source": {"kind": "generate", "mode": "t2i",
                                      "seed": 4101, "prompt": "..."}}],
  "scenes":  [{"id": "s1", "asset": "a1", "duration": 4.0,
               "motion": {"type": "push_in", "from": 100, "to": 112}}],
  "transitions": [{"between": ["s1", "s2"], "type": "cross_dissolve", "frames": 16}],
  "render": {"format": "h264", "bitrateKbps": 6000}
}
```

Canvas dimensions must be multiples of 32 — the image model rejects anything else.
`1280x720` is exact 16:9 and does not work; use `1024x576`, `1536x864`, `2048x1152`.

## Measured results

From a real run on an M4 Pro / 51.5 GB (`docs/evidence/`):

| step | measurement |
|---|---|
| capabilities | 7/7 Rust apps probed, `text_filters: false` |
| 3 assets | generated, hashed, cached, reusable |
| transitions | 2 applied, count asserted against the spec |
| motion | frame diff 6.71 / 28.34 / 0.94 (all > 0.3) |
| duration | 12.01 s vs 12.00 expected (`sum` model) |
| container | h264 1024×576, 288 frames, 24 fps, clean decode |
| steps | **17 verified, 5 requested_only, 0 failed** |

## Known limitations

- **Apple Silicon only.** MLX has no other backend.
- **~17.8 GB of weights** must be present; they are not in this repo.
- **`ffmpeg` here has no `subtitles`/`ass`/`drawtext`.** Verified by listing the
  filter catalogue. Captions must be composited as title graphics, not burned by
  ffmpeg. `doctor` reports this so a plan cannot silently depend on it.
- **Dissolves do not shorten the timeline** on this NLE (measured: 3×4 s with two
  16-frame dissolves renders 12.01 s). The duration check accepts either model
  and records which matched.
- **No audio stage yet.** The audio lessons (per-item normalisation, mastering the
  export) are documented in `skills/render-qa` but not implemented here.
- **EffectCraft is not wired into the runner.** Per-shot compositing is proven in
  the `artcraft-suite-headless` skill, not by this repo's end-to-end test.
- **License unresolved.** No `LICENSE` file ships until the owner chooses one.

## Documentation

- `docs/architecture.md` — layers and why adapters, not one interface
- `docs/installation.md` — clean and existing-installation paths
- `docs/workflow.md` — the six stages with real output
- `docs/verification.md` — what is checked at each level
- `docs/troubleshooting.md` — symptom → cause → fix
- `docs/security.md` — what this will not do
- `docs/environment-report.md` — the machine this was built on
- `docs/evidence/` — a real manifest and a real frame
