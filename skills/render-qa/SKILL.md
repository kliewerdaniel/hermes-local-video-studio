---
name: hlvs-render-qa
description: Verify a rendered file by measuring it, not by trusting the renderer.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [qa, ffprobe, loudness, motion, encoding]
    related_skills: [hlvs-timeline-validation, hlvs-asset-provenance]
---

# Render and quality assurance

## When to use

After every export, before delivering anything.

## What gets measured

`hlvs/adapters/media.py` and the runner's `verify_output` stage:

| check | method | passes when |
|---|---|---|
| container | `ffprobe -show_streams` | h264 video stream present |
| decode | `ffmpeg -f null -` | exit 0 and empty stderr |
| duration | probe vs computed | within tolerance of sum(holds) − dissolve overlap |
| motion | frame diff inside each moving clip | > 0.3 |
| content | luma std at 3 points per scene | at least one sample > 3.0 |
| audio | `loudnorm` + decoded peak | peak ≤ 1.0, voice above bed |

## Why duration needs a computed expectation

Sum the declared holds and subtract `frames / fps` per dissolve, because a
transition overlaps two clips and shortens the timeline. Without that correction
the check fails on a correct render — or, worse, passes on a wrong one.

## The content check, and why it is not a threshold to lower

A shot can be legitimately near-black (a fade, a void, a title bed) while the
shot built from it is not. So the check samples three points and requires that at
least one carries structure — and reports the near-black fraction rather than
hiding it.

When a check fails for a legitimate reason, change **what it measures**, not the
number. A loosened threshold stops catching the real case.

## Audio

Measure loudness and true peak, never merely "an audio stream exists".

- Normalise short clips by **measured gain**, not `loudnorm` — on 3–6 s takes it
  applies unstable gain and can raise the peak.
- A balance that will not hold is per-item normalisation. If the NLE normalises
  each audio item, bake **one** mixed master instead.
- Master the export rather than trusting it: measure the decoded peak and apply
  the exact gain that lands it near 0.70, then re-measure and refuse to ship
  while it is above 1.0.

## Commands

```bash
scripts/verify-output examples/minimal-project/build/output.mp4
ffmpeg -v error -i out.mp4 -f null -                       # clean decode
ffmpeg -i out.mp4 -af loudnorm=print_format=json -f null -  # LUFS
```

## Verification

A render is done when every row above reports a measured number. The report must
distinguish `verified` from `requested_only`.
