---
name: hlvs-creative-apps
description: Drive the ArtCraft Rust suite through per-app adapters.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [artcraft, effectcraft, filmcraft, lightcraft, compositing, nle]
    related_skills: [hlvs-qwen-image, hlvs-render-qa]
---

# Creative application adapter

## When to use

Any time a task maps to a real creative app: compositing, grading, layout,
timeline assembly, export.

## The suite and what each is for

| App | Job | Binary |
|---|---|---|
| LightCraft | one consistent grade across stills | `lightcraft-cli` |
| PhotoCraft | raster work, blurs, batch actions | `photocraft-cli` |
| VectorCraft | crisp line art / HUD with alpha | `vectorcraft-cli` |
| EffectCraft | per-shot composites, camera moves, type | `effectcraft-cli` |
| FilmCraft | timeline, transitions, captions, export | `filmcraft-cli` |

Do each job in the app it belongs to. Camera moves in the NLE throw away the
compositor; a grade in the NLE throws away the raw pipeline.

## Adapter

`hlvs/adapters/filmcraft.py` wraps the NLE. It exists to prevent three specific
mistakes:

1. `--project` needs an existing file; new projects use `--save-as`.
2. `timeline.place` takes **item** ids; transitions take **sequence clip** ids.
   The adapter reads the sequence back and maps them by timeline order.
3. A transition acts on the edit point **under the playhead**. `dissolve()` sets
   the playhead first, because forgetting it produces an export with hard cuts
   and no error.

```python
from hlvs.adapters.filmcraft import FilmCraft
nle = FilmCraft(binary, "film.fcproj")
nle.create("film", 1024, 576, 24)
item = nle.import_media("still.png")
nle.place(item, "V1", 0.0, 4.0)
clips = nle.placed_clips()          # clip ids, in timeline order
nle.dissolve(clips[1]["clip"], 4.0, frames=16)
nle.motion(clips[0]["clip"], 0.0, 4.0, 100, 112, 1024, 576)
nle.export("out.mp4", 6000)
```

## Silent-drop discipline

These tools accept an unknown parameter and ignore it. Two consequences:

- If a command returns success and the output is unchanged, suspect the
  parameter, not the render.
- Two exports with identical byte counts mean the setting did not apply.

## Not every property is a 2-vector

`Turbulent Displace.Amount` is a scalar; keyframing it with `[70,70]` fails.
Read `props` for the property before scripting a keyframe on it.

## Verification

Never accept an exit code as evidence. `hlvs-render-qa` measures the file.
