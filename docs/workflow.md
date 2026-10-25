# Workflow

A brief becomes a file through six stages — the path `scripts/run-project` takes.

## 1. Write the project

Start from `examples/minimal-project/project.json`. Describe assets, scenes,
motion and transitions — not tool commands.

## 2. Validate

```bash
scripts/validate-project my-project/project.json
```

Rejects bad dimensions, unknown operations, dangling references and non-adjacent
transitions. Everything expensive happens after this gate.

## 3. Probe

```bash
scripts/doctor --strict
```

Non-zero exit if the Qwen studio is down or an app is missing — before a
generation is attempted, not after it fails.

## 4. Generate assets

Each `kind: generate` asset is produced through the Qwen adapter, hashed, and
cached in `build/assets.json`. A re-run reuses the file. `kind: file` assets are
hashed in place.

## 5. Assemble

- create the NLE project with `--save-as` (not `--project`)
- import and place each scene at its computed start
- **read the sequence back** and map sequence clip ids by timeline order
- apply motion per scene using absolute times
- apply each dissolve after moving the playhead to that cut
- assert `transitions_count == expected`, and refuse to export otherwise

## 6. Render and verify

Export h264, then measure: container, clean decode, duration against a computed
expectation, frame difference inside each moving clip, luma structure at three
points per scene.

## The computed duration

```
expected = sum(scene durations) - sum(dissolve frames) / fps
```

A dissolve overlaps two clips, so the timeline is shorter than the sum of holds.
Checking against the raw sum fails on a correct render.

## What a run looks like

```
OK   capabilities               {'rust_apps_found': 7, 'qwen_reachable': True, ...}
OK   asset:a_approach           {'path': '...', 'sha256': '...', 'job_id': '...'}
OK   place:s1                   {'item_id': 1}
OK   nle:map_clips              {'clip_ids': [1, 2, 3]}
OK   motion:s1                  {}
OK   transition:s1->s2          {}
OK   verify:transitions         {'count': 2}
OK   render                     {'bytes': ..., 'duration': ...}
OK   verify:container           {'codec': 'h264', 'width': 1024, 'height': 576}
OK   verify:decode              {'clean': True}
OK   verify:duration            {'expected': ..., 'actual': ...}
OK   verify:motion              {'frame_diff': {'s1': ...}}
OK   verify:content             {'luma_std': {'s1': [...]}}
```

`OK` means verified. A `REQ` line is a step whose command was accepted but which
nothing measured — the report never presents those as done.
