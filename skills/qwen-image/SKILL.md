---
name: hlvs-qwen-image
description: Generate or edit images with the local Qwen-Image-2.1-Turbo studio.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [image-generation, qwen-image, mlx, apple-silicon, image-edit]
    related_skills: [hlvs-environment-discovery, hlvs-creative-apps]
---

# Qwen image production

## When to use

Producing or restaging stills locally: a shot list, a sequence that must hold one
subject's identity, or a background replacement. Not for video.

## Start it

```bash
cd ~/Projects/qwen-image-studio && ./start.sh    # -> http://127.0.0.1:8787
```

Weights are MLX Q8 (~17.8 GB), 8-step turbo schedule, loaded on first generate.

## Adapter

`hlvs/adapters/qwen.py` — standard library only.

```python
from hlvs.adapters.qwen import QwenAdapter
q = QwenAdapter()
q.status()
q.generate("a lighthouse in fog", mode="t2i", width=1024, height=576, seed=4101)
# -> {"job_id", "path", "seconds", "mode", "seed", "width", "height"}
```

`generate()` returns only after the job reaches `done` **and** `result.path`
exists on disk. A job that reports done with no file raises — it is not a result.

## Constraints that will bite

- **Dimensions must be positive multiples of 32.** `1280x720` is exact 16:9 and
  is rejected. Use `1024x576`, `1536x864`, `2048x1152`.
- The upload field is `images`, not `images[]`.
- `edit` / `inpaint` require at least one reference; the first is the edit source.
- Outputs land in the studio's own `outputs/` directory — always read
  `result.path`, never construct a path.
- **One mode per server lifetime.** Switching t2i↔edit mid-batch loads a second
  17.8 GB copy and the OS kills the process, taking the batch with it.
- Generation is serialised. A batch owns the machine: do not run another model
  or a long GPU job alongside it.

## Identity across a sequence

Source every frame from the **original** reference, never from the previous
output. Open the prompt with the environment rather than the subject, and name
the unwanted artifacts explicitly. For a person, verify identity by cropping to
the face at full resolution — a contact sheet will misread backlit hair as a bald
head.

## Failure handling

- `Connection refused` → the server died (usually OOM). Restart; the manifest
  resume in the runner means finished assets are not regenerated.
- Abort after two consecutive failures rather than grinding a bad parameter.

## Verification

A generated file is not a good image. Check `sha256`, dimensions, and luma
structure per frame. "Job done" means a PNG exists.
