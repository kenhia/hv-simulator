# Sprint 010 — Universe foundation: compiler + orbits + binary ephemeris (Phase 2a)

First **Phase 2a** slice (design in `004`/`006`). Stand up the data→engine
pipeline and make the engine place bodies in *any* built system at time T —
including the **binary** Manticore — by compiling the dataset into the frozen
universe artifact and loading it. **No travel yet** (that's the DES work in 2b).

## Goal

`just compile-data` turns `data/` JSON into the read-only SQLite **universe
artifact** (the v0.1.0 contract); the engine loads it and answers "where is body
X in system Y at T," with binary primaries handled. Sol stays on its validated
JPL ephemeris (special-case); fictional systems use derived orbits.

## Decisions baked in (from this session)

- **Focused slice:** compiler + orbit-derivation + engine artifact-loading &
  binary-aware placement. **Defer** the coordinate-frame solver (inter-system,
  2b) and the **DES core** (2b travel). No routes/wormholes/hyper this sprint.
- **Sol special-case:** the engine keeps its JPL Sol ephemeris in code; the
  artifact drives only fictional systems. Contract stays **v0.1.0**.
  **README note (Ken):** we take the artistic license of keeping **Sol tied to
  the actual current positions of the real planets** (JPL approximate elements),
  while Honorverse systems use fabricated/derived orbits.

## Scope

### `tools/universe-compiler/` (own `pyproject.toml`)
- Read `data/` JSON → **validate** against `data/schema/*.schema.json` →
  **resolve FKs** (parent_star, nation refs, wormhole endpoints; report dangling)
  → **namespace ids** (`system:local`, e.g. `manticore:titan`) → write a
  read-only SQLite matching `contracts/universe-artifact/schema.sql`, inserting
  `schema_meta.version`.
- Output to a build path (e.g. `build/universe.db`, gitignored) — the artifact is
  derived, not committed.

### `tools/orbit-derive/` (own `pyproject.toml`)
- Fill in-system **Keplerian orbits** for built fictional systems, all
  `canon:false`, `determined:true`, written back to the `data/` JSON source.
- Honor the canon anchors: **Manticore year 1.73 T-yr** → period → `a_au` via
  Kepler from Manticore-A's mass; Grayson ~13.5 lm, Medusa ~7 lm, Masada ~¼
  Grayson, etc. For un-anchored planets, a documented monotonic spacing
  heuristic (geometric / Titius-Bode-like) consistent with `orbit_index`, with
  habitable worlds near the star's habitable zone. Near-circular `e`, small `i`,
  seeded mean-anomaly phase; `period_days` from Kepler. First-pass and clearly
  fabricated — refine later.

### Engine (in `engine/`)
- Load the universe artifact (path via env, e.g. `HVSIM_UNIVERSE_DB`).
- Extend the ephemeris to **per-system / binary primaries**: a system's origin is
  its barycenter; binary stars orbit the barycenter (from the `binaries` block —
  separations in lmin, e, period derived from masses); bodies orbit their
  `parent_star`; moons orbit their `parent_body`. Reuse `_orbital_to_xyz`.
- A **system-aware position resolver**: `sol` → the existing JPL path; other
  systems → artifact-driven. One interface, two backends.
- Surface it: extend the `where-is` CLI to take a system, and implement the
  frozen **read endpoints** (`GET /systems`, `/systems/{id}`,
  `/systems/{id}/bodies?at=`, `/bodies/{id}/state?at=`). (Descope to CLI-only if
  the endpoints bloat the sprint.)

### Orchestration & docs
- `justfile`: `derive-orbits`, `compile-data` (derive + compile), and extend
  `check` to cover the new tool tests + a compile smoke. README/CLAUDE.md: the
  data→artifact→engine flow + the Sol artistic-license note.

## Out of scope

- **Coordinate-frame solver / inter-system distances** — 2b.
- **DES core, routes, travel, wormholes, hyperspace** — 2b/2c.
- **Authoring Sol into the dataset** — kept special-case.
- **Deploying the artifact to kubsdb / baking it into the image** — later (2a is
  local placement + tests; the deployed instance still runs Phase-1 Sol).
- **UI** — 2.5.

## Tasks

- [x] `tools/universe-compiler`: JSON → validate → resolve FKs → namespace ids →
      SQLite artifact (+ `schema_meta` version); output to `build/` (gitignored).
- [x] `tools/orbit-derive`: fill fictional in-system orbits from canon anchors +
      a documented spacing heuristic; write back to `data/` JSON (canon:false).
- [x] Engine: load the artifact; binary-aware per-system ephemeris; system-aware
      resolver (Sol = JPL special-case, others = artifact).
- [x] Engine surface: `where-is <system> <body>`; read endpoints from the OpenAPI.
- [x] `justfile`: `derive-orbits`, `compile-data`; extend `check`.
- [x] Tests: compiler (sample compile + FK/namespace), orbit-derive (anchors
      honored), engine binary placement (Manticore-A/B separation in canon range;
      a planet placed around its parent star); Sol unchanged.
- [x] README/CLAUDE.md: data→artifact→engine flow + Sol artistic-license note.

## Acceptance criteria

- `just compile-data` produces a **valid** SQLite artifact from `data/` matching
  the contract (FKs resolved, ids namespaced, `schema_meta.version` set).
- `orbit-derive` fills the built fictional systems' in-system orbits
  (`canon:false`, `determined:true`); **Manticore's derived period ≈ 1.73 T-yr**
  within tolerance.
- The engine loads the artifact and places bodies per-system at T, **including
  binary Manticore**: stars sit at canon-consistent barycentric separation
  (650–827 lmin range), planets orbit their parent star, moons their planet.
  `where-is manticore sphinx` (or the endpoints) returns a plausible position.
- **Sol is unchanged** — its JPL ephemeris and all 63 Phase-1 tests still pass.
- Gate green: engine tests + the new tool tests + a compile smoke (`just check`).

## Notes / decisions

- Derived orbits are **fabrication** — flagged `canon:false`; the heuristic is
  documented so a future canon source (or hand-tuning) can override cleanly.
- The artifact is a **build output** (gitignored); `data/` JSON stays the source
  of truth. Engine reads the compiled DB, never loose JSON.
- Contract stays **v0.1.0** (Sol special-case avoids needing rate columns). If we
  later unify Sol into the dataset, that's the v0.2.0 rate-column bump noted in
  the 009 contract discussion.
- Tools may share a tiny data-model lib later; for now each is self-contained.

## Outcome — DONE

- Shipped on branch `sprint-010-universe-foundation`. `just check` green: engine
  (68 tests incl. 5 universe tests) + `universe-compiler` + `orbit-derive` tests;
  ruff/format clean. No regression to Sol (Phase-1 tests pass).
- **`tools/orbit-derive/`**: filled 26 planet orbits across the 4 built systems
  (canon:false), honoring anchors — Manticore's derived period round-trips to
  **1.730 T-yr**. Fabricates stellar mass from spectral class where canon lacks it.
- **`tools/universe-compiler/`**: `data/` JSON → read-only SQLite artifact;
  validates (best-effort), resolves FKs with **deferred checks + stubbing** (6
  unbuilt nations stubbed), system-namespaces ids. `just compile-data` →
  `build/universe.db` (4 systems, 31 bodies, 13 classes, 30 ships).
- **Engine `hvsim.universe`**: loads the artifact; **binary-aware** placement —
  stars split a Keplerian relative orbit by mass ratio (separation falls in the
  canon 650-827 lmin band by construction); planets orbit their star, moons their
  planet. `resolve_position` routes Sol → JPL, others → artifact. CLI `where-is
  --system`; read endpoints `GET /systems`, `/systems/{id}/bodies`.
  Verified: Manticore placement reads e.g. Manticore 1.49 AU / Sphinx 2.40 AU
  from their star; Manticore-B worlds around B.
- **Sol special-case** documented (artistic license: Sol tracks real current
  planet positions). Contract stayed **v0.1.0**.
- Deferred to 2b (as scoped): coordinate frame / inter-system distance, the DES
  core / travel, and compiling wormholes + hyperspace into the artifact.
- **Phase 2.5 flavor (noted):** the UI will want click-a-ship→specs,
  body/system→detail/lore. No impact on 010 — the artifact is a *recompilable*
  lean projection over `data/` JSON, which already retains all flavor
  (lore, armament `by_arc`, dimensions, crew, timelines). When 2.5 needs it we add
  flavor columns/tables in a **v0.2.0** bump and recompile; nothing is lost by
  keeping 010 physics-lean. Build the compiler as a clean, extensible JSON→SQLite
  projection (add-columns-later, never lossy by design).
