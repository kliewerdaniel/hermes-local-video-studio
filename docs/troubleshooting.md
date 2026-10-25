# Troubleshooting

First question, always: **was this step requested, or verified?** Read
`build/manifest.json`, find the step, check its status. A `requested_only` step
means nothing measured it, and the tool may have done nothing at all.

## Installation

| symptom | cause | fix |
|---|---|---|
| `doctor` shows `missing` for every app | wrong paths | binaries live at `~/Projects/<app>/target/release/<app>-cli` |
| an app is found but `runs: false` | stub or wrong binary | run `<cli> commands` by hand |
| `photocraft` missing though installed | release-only lookup | the debug fallback covers it |
| `ImportError: numpy` | optional measurement deps absent | `pip install numpy pillow` |
| `text_filters: no` | this ffmpeg has no libass/drawtext | composite captions as title graphics |

## Generation

| symptom | cause | fix |
|---|---|---|
| `Connection refused` | server died, usually OOM | restart; assets resume from cache |
| dies mid-batch after a mode change | second 17.8 GB variant loaded | one mode per server lifetime |
| `dimensions must be positive multiples of 32` | e.g. 1280×720 | use 1024×576 or 1536×864 |
| `edit needs at least one reference` | wrong upload field | the field is `images`, not `images[]` |
| job `done` but path missing | adapter raises rather than guessing | inspect `result.path` |
| very slow | generation is serialised | budget minutes per frame |

## Assembly

| symptom | cause | fix |
|---|---|---|
| `no edit point at the playhead` | playhead not moved, or item id used as clip id | `dissolve()` sets it; map clip ids from the sequence |
| export succeeds, all cuts hard | dissolves silently failed | assert the count against the spec |
| clip reports `keyframes: 1` | keyframe time before clip start | pass sequence-absolute times |
| placed N clips, sequence reports fewer | an import silently failed | the runner fails instead of exporting |

## Output

| symptom | cause | fix |
|---|---|---|
| duration fails by ~1 frame per cut | expectation not corrected for overlap | subtract `frames / fps` per dissolve |
| a moving clip measures 0.00 | keyframes collapsed | check the time space |
| a shot measures empty | genuinely near-black, or a dead effect | sample 3 points; change *what* is measured, not the threshold |
| audio above 0 dBFS | the NLE loudness stage | master afterwards and re-measure |
| voice and bed at the same level | per-item normalisation | bake one mixed master |

## Recovery

Delete `build/` for a clean rebuild; delete only `build/assets.json` to
regenerate images while keeping everything else. `--no-resume` does the same for
a single run.
