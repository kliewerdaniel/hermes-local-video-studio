---
name: hlvs-timeline-validation
description: Prove transitions, keyframes and masks exist in the edit — not just in the config.
version: 1.0.0
author: Daniel Kliewer
license: MIT
category: creative
metadata:
  hermes:
    tags: [validation, transitions, keyframes, masks, verification]
    related_skills: [hlvs-creative-apps, hlvs-render-qa]
---

# Timeline and effects validation

## When to use

After any edit that claims to contain a transition, a camera move, or a mask, and
before calling that edit done.

## Configuration validation vs rendered validation

Two different questions, two different methods:

| question | method | what it proves |
|---|---|---|
| did the command land? | read the project back | the config contains it |
| did it reach the picture? | measure frames | the viewer sees it |

A dissolve can be present in the project and absent from the export. A keyframe
can exist with `keyframes: 1` and produce no movement. Only the second method
answers "is it in the film".

## Transitions: assert the expected count, not "> 0"

The classic failure is a missing `playhead.set`. Every dissolve then fails, and
the export still completes — so the film ships with hard cuts.

```python
wanted = [t for t in project["transitions"] if t["type"] == "cross_dissolve"]
got = nle.transitions_count()
if got != len(wanted):
    raise SystemExit("expected %d dissolves, sequence has %d" % (len(wanted), got))
```

`if applied == 0` is too weak: losing four of thirteen exports happily. Keep an
explicit list of cuts that are *meant* to be hard, so a strict count does not
punish a deliberate cut.

## Keyframes: time is sequence-absolute

A keyframe time that falls before the clip's start clamps onto the first
keyframe, collapsing the animation to a static frame — with no error. Always pass
the clip's absolute `start` and `start + duration`.

Verify by measurement, not by the command returning:

```python
diff = media.mean_abs_diff(out, t0, t1, tmp)   # t0/t1 well inside the clip
assert diff > 0.3, "clip is static (diff=%.3f)" % diff
```

Sample **inside** the clip. A window that overlaps a transition measures the
transition, not the animation, and will report motion on a clip that never moved.

## Masks

A mask that renders anyway is the canonical silent failure: the layer exists, the
mask attaches, every parameter reads back correctly, and the frame is wrong —
often pure black because an opaque carrier solid sat above the plate. Carrier
solids on top of a rig must be additive.

Measure the region, and exclude your own overlays from it: a burned-in subtitle
bar sitting over a "flat" region makes it read as textured (measured std 18.9
where the true value was 0.0). Print per-region means to see which pixels you
actually measured.

## Verification

`verify:transitions` must report `count == expected`. `verify:motion` must report
a `frame_diff` above 0.3 for every moving scene.
