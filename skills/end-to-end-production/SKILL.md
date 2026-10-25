---
name: hlvs-end-to-end-production
description: Run a brief through plan, generate, assemble, render and verify.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [production, orchestration, pipeline, end-to-end]
    related_skills: [hlvs-video-planning, hlvs-qwen-image, hlvs-render-qa]
---

# End-to-end video production

## When to use

A brief must become a file. This skill coordinates the others; it invents nothing.

## The chain

```
brief -> project.json -> validate -> capabilities -> generate assets
      -> assemble (place, motion, transitions) -> render -> verify -> manifest
```

## Run it

```bash
scripts/doctor                                     # is the machine able?
scripts/validate-project examples/minimal-project/project.json
scripts/run-project examples/minimal-project/project.json
```

`run` stops at the first failed stage and writes `build/manifest.json` with what
it managed to verify. It does not continue past a failure to look productive.

## What the run reports

Per step: `OK` (verified), `REQ` (requested, unmeasured), `FAIL`, `SKIP`. The
summary line counts each. A run with `failed: 0` and several `requested_only` is
a partial success and says so.

## Dry run

```bash
scripts/run-project examples/minimal-project/project.json --dry-run
```

Validates the spec and probes capabilities without spending GPU time. Use it
after every edit to the project file.

## Resume

Assets are cached by id and hash in `build/assets.json`. A killed run re-starts
from the first missing asset rather than regenerating everything. `--no-resume`
forces a clean rebuild.

## Failure handling

- A failed asset generation aborts before assembly — a film with a missing shot
  is not worth assembling.
- A transition count mismatch **refuses to export**. That is deliberate: an
  export that completes is not evidence the edit contains what you asked for.
- If verification fails, the file is kept (so it can be inspected) and the
  manifest records the measurement that failed.

## Verification

The run is complete when `manifest.json` reports `failed: 0` and every step that
claims success carries a `verified` measurement.
