# Verification

## Levels

| level | command | needs | proves |
|---|---|---|---|
| unit | `python3 -m unittest discover -s tests/unit` | nothing | schema and provenance logic |
| integration | `python3 -m unittest discover -s tests/integration` | ffmpeg | media measurement works on real files |
| smoke | `scripts/smoke` | ffmpeg | the above plus project validation |
| capability | `scripts/doctor` | installed apps | the machine can do the work |
| end-to-end | `scripts/run-project examples/minimal-project/project.json` | + model | a film exists and measures correctly |

## What the end-to-end run checks

Recorded in `build/manifest.json`, one step each:

```
validate              scenes, assets counted
capabilities          7 apps, qwen reachable, text filters
asset:<id>            path, sha256, job id, generation seconds
nle:create            project file exists
place:<id>            item id returned
nle:map_clips         sequence clip ids, mapped by timeline order
motion:<id>           scale keyframes requested
transition:<a>-><b>   playhead moved, dissolve requested
verify:transitions    count == expected   (fatal on mismatch)
render                bytes, duration, sha256
verify:container      codec, width, height, duration
verify:decode         clean decode
verify:duration       within tolerance of computed expectation
verify:motion         frame diff per moving clip
verify:content        luma std at 3 points per scene
```

## The distinction the report preserves

Every step is one of:

- **verified** — a measurement is attached
- **requested_only** — the tool accepted the command; nothing measured it
- **failed** — with the error
- **skipped** — deliberately not applicable

A run that reports `failed: 0` but several `requested_only` is a partial success,
and the summary says so. That is the intended behaviour, not a bug.

## Independent inspection

Do not rely only on this repo's own numbers. The rendered file can always be
checked with plain tools:

```bash
ffprobe -v error -show_entries format=duration,size -show_entries \
  stream=codec_name,codec_type,width,height -of default=nw=1 output.mp4
ffmpeg -v error -i output.mp4 -f null -        # clean decode
ffmpeg -y -ss 2.0 -i output.mp4 -frames:v 1 f.png   # look at a frame
```

## Results from the recorded run

`scripts/run-project examples/minimal-project/project.json`, M4 Pro / 51.5 GB,
macOS 26.6.2, Python 3.9.6, ffmpeg 9.0.2.

```
OK   capabilities               {'rust_apps_found': 7, 'qwen_reachable': True, 'text_filters': False}
OK   asset:a_approach           generated, sha256 recorded, cached
OK   asset:a_lantern            generated, sha256 recorded, cached
OK   asset:a_dark               generated, sha256 recorded, cached
OK   nle:create                 {'project_exists': True}
OK   place:s1                   {'item_id': 8}
OK   place:s2                   {'item_id': 10}
OK   place:s3                   {'item_id': 12}
OK   nle:map_clips              {'clip_ids': [9, 11, 13]}
REQ  motion:s1..s3             command accepted; measured separately below
REQ  transition:s1->s2, s2->s3  command accepted; measured separately below
OK   verify:transitions         {'count': 2}
OK   render                     {'bytes': 9264092, 'duration': 12.01, 'sha256': '9ae966c8...'}
OK   verify:container           {'codec': 'h264', 'width': 1024, 'height': 576}
OK   verify:decode              {'clean': True}
OK   verify:duration            {'actual': 12.01, 'model': 'sum', 'expected': 12.0}
OK   verify:motion              {'frame_diff': {'s1': 6.707, 's2': 28.343, 's3': 0.935}}
OK   verify:content             {'luma_std': {'s1': [74.8, 74.5, 74.3], ...}}
```

**17 verified, 5 requested_only, 0 failed.**

Independent ffprobe of the same file: h264, 1024x576, 288 frames, 24/1 fps,
12.010 s, 9,264,092 bytes, clean decode. A frame decoded at 2.0 s was inspected
and is a correctly rendered lighthouse — not a placeholder.

## What this run does NOT prove

- That the pipeline works on a clean machine. It was built against an existing
  installation; the clean path is documented but **untested**.
- That other resolutions behave identically. Only 1024x576 was measured here.
- That the audio stage works. There is no audio stage yet.
- That EffectCraft compositing works inside this runner. It is proven separately
  in the `artcraft-suite-headless` skill, not by this end-to-end test.
