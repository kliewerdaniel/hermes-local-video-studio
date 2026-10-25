---
name: hlvs-asset-provenance
description: Track prompts, hashes and transformations for every asset.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [provenance, manifest, hashing, reproducibility]
    related_skills: [hlvs-video-planning, hlvs-render-qa]
---

# Asset and provenance management

## When to use

Every run, automatically — and especially when a result must be defensible later.
The manifest is the difference between "we made a film" and "here is what produced
each frame".

## What is recorded

`hlvs/provenance.py` writes `manifest.json` in the work directory:

- every step, with **`requested`** and **`verified`** kept apart
- status per step: `verified` / `requested_only` / `failed` / `skipped`
- `sha256` and byte size for every artifact
- timings, job ids, seeds, and the generation duration per asset

## The distinction that matters

```python
StepResult(step="motion:s1", requested={"scale_from": 100, "scale_to": 112})
# status == "requested_only" — the command was accepted, nothing measured it

result.verify(frame_diff={"s1": 4.21})
# status == "verified" — a frame difference was measured
```

`verify()` **raises** if called with no measurement. A step cannot be promoted to
verified by optimism.

## Idempotence and resume

Generated assets are cached in `build/assets.json` keyed by asset id with their
hash. A re-run reuses an existing file instead of spending another four minutes
of GPU. Delete the cache, or pass `--no-resume`, to force regeneration.

## Commands

```bash
python3 -c "from hlvs.provenance import sha256_file; print(sha256_file('x.png'))"
cat build/manifest.json | python3 -m json.tool | head -40
```

## Verification

`manifest.json.summary` must show `failed: 0`. A manifest with steps in
`requested_only` is an honest record of work that was not confirmed — it is not
a pass.
