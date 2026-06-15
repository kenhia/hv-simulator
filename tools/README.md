# tools/

Standalone tools, each in its own `tools/<name>/` with its own `pyproject.toml`
(or `Cargo.toml` if a tool ever goes Rust). They build the universe artifact the
engine consumes and help author the dataset; they are **not** part of the engine.

Planned (Phase 2a+):

- `universe-compiler` — `data/` JSON → validate → resolve FKs → namespace ids →
  the read-only SQLite [`contracts/universe-artifact`](../contracts/universe-artifact).
- `coordinate-frame` — triangulate canon bearings/distances into a fabricated
  Sol-origin galactic frame.
- `orbit-derive` — first-pass Keplerian elements from canon anchors.
- `route-validator` — wormhole-graph connectivity / dangling-terminus checks.

The dataset's **scribe skills** (`honorverse-{system,ship,wormhole}-scribe`) live
in the repo's `.claude/skills/` and write the JSON source of truth under `data/`.
