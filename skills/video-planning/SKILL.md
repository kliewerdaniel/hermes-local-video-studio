---
name: hlvs-video-planning
description: Turn a creative brief into a validated, executable project spec.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [planning, schema, project-spec, timeline]
    related_skills: [hlvs-asset-provenance, hlvs-end-to-end-production]
---

# Video planning

## When to use

Whenever a brief has to become something executable. The output is a JSON file,
not prose.

## The format

`schema_version`, `project` (name, canvas, fps), `assets[]`, `scenes[]`,
`transitions[]`, `render`. Full definition in `schemas/project.schema.json`;
the authority the runner consults is `hlvs/schema.py`.

```json
{
  "schema_version": "1.0",
  "project": {"name": "lighthouse", "canvas": {"width": 1024, "height": 576}, "fps": 24},
  "assets": [{"id": "a1", "source": {"kind": "generate", "mode": "t2i",
                                     "seed": 4101, "prompt": "..."}}],
  "scenes": [{"id": "s1", "asset": "a1", "duration": 4.0,
              "motion": {"type": "push_in", "from": 100, "to": 112}}],
  "transitions": [{"between": ["s1", "s2"], "type": "cross_dissolve", "frames": 16}],
  "render": {"format": "h264", "bitrateKbps": 6000}
}
```

## Why validate before generating

A malformed spec discovered after six generations has cost an hour. The same
error found by `validate` costs a second. Validation rejects:

- canvas dimensions that are not multiples of 32 (the model refuses them)
- unsupported motion types, modes, transition types, formats — an explicit
  allowlist, so a typo cannot become a silent no-op
- scene→asset references that do not resolve
- transitions between scenes that are not adjacent
- duplicate ids, non-positive durations, missing prompts
- `kind: file` paths that do not exist

## Durations and the runtime budget

Hold each scene for its intended duration and **assert the total**, accounting
for dissolve overlap (each dissolve shortens the timeline by `frames / fps`). A
cut that lands exactly on a stated floor is one rounding error from being under
it; aim mid-range.

## Verification

`scripts/validate-project <file>` must print `VALID` before any run.
