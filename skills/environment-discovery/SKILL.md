---
name: hlvs-environment-discovery
description: Discover the local video-production environment before planning work.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [discovery, doctor, capabilities, local-inference, artcraft]
    related_skills: [hlvs-qwen-image, hlvs-creative-apps]
---

# Environment discovery

## When to use

First, always — before planning a shot list, before generating anything, before
promising a capability. Also whenever a run fails in a way that suggests a missing
tool rather than a bad parameter.

## What it does

`scripts/doctor` locates and **probes** every dependency:

- host, CPU, cores, RAM, python
- `ffmpeg` / `ffprobe`, and specifically whether the build has text filters
- the seven ArtCraft binaries (release preferred, debug fallback, then `PATH`)
- whether the Qwen studio answers on `:8787`

## Inputs / outputs

| | |
|---|---|
| inputs | none |
| outputs | human summary on stdout; `--json` for the full report |
| exit | `0` ok, `2` with `--strict` when something required is missing |

## Commands

```bash
scripts/doctor
scripts/doctor --json > capabilities.json
scripts/doctor --strict        # non-zero if qwen is down or an app is missing
scripts/doctor --no-probe      # locate binaries only, do not execute them
```

## Found is not the same as working

A binary on disk that cannot answer `commands` is not a capability. The probe
runs each CLI and records `runs: true/false` separately from `found: true/false`.
Report the two separately; never upgrade "found" into "works".

## The finding that changes the plan

This machine's `ffmpeg` has **no `subtitles`, `ass` or `drawtext` filter**.
Verified by listing the filter catalogue, not by assuming. The consequence is
concrete: no ffmpeg invocation will ever burn a subtitle here, so captions must
be composited as title graphics in the NLE or the compositor. Check
`text_filters` before promising subtitles.

## Failure handling

- Qwen unreachable → `mode: generate` assets cannot be produced. Either start the
  studio or switch those assets to `kind: file` with existing images.
- A Rust app missing → the stages that need it must be skipped and reported, not
  silently omitted.

## Verification

The report is the verification: every line is a value read from the machine.
Re-run it after any install and diff against the previous report.
