---
name: hlvs-troubleshooting
description: Diagnose and recover from local video-production failures.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [troubleshooting, recovery, debugging, failures]
    related_skills: [hlvs-environment-discovery, hlvs-render-qa]
---

# Troubleshooting and recovery

## When to use

A stage failed, an output is wrong, or a tool "succeeded" and nothing happened.

## The first question, always

**Was it requested, or was it verified?** Read `build/manifest.json` and find the
step. If its status is `requested_only`, nothing measured it — the tool may have
done nothing at all. Most of the failures below are that, in disguise.

## Symptom → cause

| symptom | likely cause | fix |
|---|---|---|
| `Connection refused` on :8787 | model server OOM-killed | restart; assets resume from cache |
| generation dies mid-batch | mode switch loaded a 2nd 17.8 GB variant | one mode per server lifetime |
| `dimensions must be positive multiples of 32` | 1280x720 or similar | use 1024x576 / 1536x864 |
| `edit needs at least one reference` | wrong upload field name | the field is `images`, not `images[]` |
| export completes, cuts are hard | `playhead.set` missing before the transition | the adapter sets it; assert the count |
| clip reports `keyframes: 1` | keyframe time before clip start | use sequence-absolute times |
| frame is pure black, layers look right | opaque carrier solid above the plate | set the carrier to additive |
| glow/rays/threads render black | shape path has no Fill | add a Fill and set its colour |
| subtitle track present, no text in picture | captions are data, not pixels | composite title graphics; check `text_filters` |
| two exports, identical byte count | the setting was dropped | compare `bytes` between runs |
| audio clips above 0 dBFS | export loudness stage | master afterwards; refuse to ship > 1.0 |
| voice and bed arrive at the same level | per-item normalisation | bake one mixed master |

## Bounded retries

Retry a transient failure (a refused connection, a timeout) at most twice. Do not
retry a parameter error — it will fail identically and burn GPU time. After two
consecutive failures of the same kind, stop and report.

## Reporting

Say which steps failed, what the measurement was, and what remains unverified.
Do not describe an unmeasured step as complete, and do not silently skip a stage
to make a run go green.
