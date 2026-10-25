# Architecture

## The one rule

> An operation is not done because a command returned 0. It is done when
> something measured the result.

Everything below follows from that. `StepResult` keeps `requested` and `verified`
in separate fields, and `verify()` raises if it is called without a measurement.
A step cannot be promoted to "verified" by optimism.

## Layers

```
brief
  |
  v
project.json  ──(validate: schema + allowlist)──> reject before any GPU time
  |
  v
capabilities (doctor)  ──> is the machine able?  no -> stop, report
  |
  +--> QwenAdapter ................. stills (t2i / edit)
  |
  +--> FilmCraft adapter ........... place, motion, transitions, export
  |        (EffectCraft, LightCraft, PhotoCraft, VectorCraft plug in here)
  |
  v
media measurement  ──> ffprobe / ffmpeg / frame diffs / loudness
  |
  v
manifest.json  ──> per-step requested + verified + hashes
```

## Responsibilities

| layer | owns | refuses |
|---|---|---|
| `schema.py` | what a project may say | unknown ops, bad dimensions, dangling refs |
| `capabilities.py` | what the machine has | claiming a tool exists because a path exists |
| `adapters/qwen.py` | image generation | returning before `result.path` exists |
| `adapters/filmcraft.py` | timeline, transitions, export | letting item ids be used as clip ids |
| `adapters/media.py` | measurement | trusting any renderer's own report |
| `runner.py` | ordering, resume, gating | continuing past a failure to look productive |
| `provenance.py` | the record | marking a step verified with no evidence |

## Why adapters and not one interface

The tools are not interchangeable. FilmCraft needs `--save-as` then `--project …
--save`; EffectCraft saves from inside its script; LightCraft and VectorCraft are
stateless one-shots. Their id spaces differ *within* a single app — FilmCraft's
`timeline.place` takes item ids while `applyVideoTransition` takes sequence clip
ids. A single unified interface would have to lie about all of this. Adapters
encode each tool's real shape and expose a small vocabulary on top.

## Why the project format is app-independent

The spec says "a 4-second scene with a push-in and a 16-frame dissolve". It does
not say "call `effects.setParam`". App-specific settings live in the adapters, so
the same project can be executed by a different backend later without rewriting
the creative intent.

## Failure is a first-class outcome

`run()` returns as soon as a stage fails. It does not attempt later stages to
appear complete. Three failures are deliberately fatal even though the underlying
tool reports success:

1. a transition count that does not match the spec — refuses to export
2. a decode error in the rendered file
3. a moving clip that measures static

Each of these is a case where the tool would happily hand back a broken
deliverable.
