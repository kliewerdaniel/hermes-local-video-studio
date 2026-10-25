# Security and safety

## What this system will not do

- It does not run arbitrary shell. Every subprocess is a specific binary with
  specific arguments assembled by an adapter; there is no `shell=True` path for
  project-supplied strings.
- It does not write outside its work directory (plus the Qwen studio's own
  `outputs/`, which is where that tool writes by design).
- It does not upload anything. All inference is local; no network call leaves the
  machine except to `127.0.0.1`.
- It does not read credentials. Nothing in the package inspects environment
  variables, keychains, or dotfiles.

## Path handling

`kind: file` assets are resolved relative to the project file and must exist
before the run starts. The validator rejects a missing path rather than letting a
generation run against nothing.

## Subprocess timeouts

Every adapter call carries a timeout: 25 s for capability probes, 120 s for
project creation, 1800 s for generation and export. A hung tool fails the step
instead of hanging the run.

## Bounded retries

Transient failures (connection refused, timeout) may be retried twice. Parameter
errors are not retried — they fail identically and cost GPU time.

## Provenance as an audit trail

Every artifact is hashed. `manifest.json` records what was requested, what was
measured, and what the measurement was. If a claim is later questioned, the
manifest shows whether it was ever verified or only requested.

## Model weights and media

Neither is committed. `.gitignore` excludes `*.mp4`, `*.png`, `*.wav`, `*.fcproj`
and the `build/` directories. A clone is small; a run produces local artifacts.

## Licensing

MIT. The repository ships a `LICENSE` file and every skill declares
`license: MIT` in its frontmatter, so the code and the skills carry the same
terms.
