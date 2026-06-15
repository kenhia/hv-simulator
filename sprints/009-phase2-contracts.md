# Sprint 009 — Monorepo + boundary contracts (Phase 2.0)

Implements **Phase 2.0** from `planning/004-project-plan.md` (design in `006`).
The foundation sprint for the galaxy re-founding: restructure into a monorepo,
migrate the dataset in, and **freeze the two boundary contracts** that let us
"build in Python now, port the engine to Rust later" cheaply. **No new engine
behavior** — Phase 1 stays exactly as functional (and deployable) as today.

## Goal

A monorepo with `engine/ tools/ data/ contracts/ ui/`, the existing engine moved
under `engine/` and still green + shippable, the Honorverse dataset migrated to
`data/` under its own CC BY-SA license, and **versioned v0.1.0 contracts**: the
universe-artifact (compiled SQLite) schema and the engine OpenAPI spec.

## Decisions baked in (from 006 + this session)

- **Move the working engine into `engine/`** (one engine, always shippable; DES
  re-founding happens *inside* it in 2a+).
- **Migrate `/gratch/Honorverse-Data` into `data/`** (single source of truth;
  scribe skills come along).
- **Scope = contracts + scaffold only** — stubs validate, but no new endpoints or
  compiler logic this sprint.
- **Licensing:** root MIT; `data/` carries its own CC BY-SA 3.0 `LICENSE` +
  `ATTRIBUTION.md` (per-directory).
- **Contracts are the language-agnostic seam** → live in top-level `contracts/`.

## Scope

### Monorepo restructure (keep Phase 1 working)
- `git mv src/hvsim → engine/src/hvsim`, `tests → engine/tests`; engine gets its
  own `pyproject.toml`/`uv.lock`. Update everything that referenced the old paths:
  `Dockerfile`, `deploy/compose.yaml` build context, the root `justfile`,
  `where-is` entry point, README/CLAUDE.md.
- Top-level layout: `engine/`, `tools/` (scaffold), `data/`, `contracts/`,
  `ui/` (placeholder), root `justfile` orchestrating across them.
- The deployed kubsdb service must still build and run from the new layout.

### Dataset migration
- Move the dataset into `data/` preserving structure (`systems/ nations/ ships/
  wormholes/ hyperspace/ schema/ planning/ README ATTRIBUTION`).
- Add `data/LICENSE` (CC BY-SA 3.0 full text); keep `data/ATTRIBUTION.md`.
- Relocate the scribe skills (`honorverse-{system,ship,wormhole}-scribe`) to the
  repo's `.claude/skills/` so they stay invocable; note their scripts can become
  `tools/<name>/` packages in 2a (not this sprint).

### Contract 1 — universe-artifact (compiled SQLite) — `contracts/universe-artifact/`
- Versioned **SQL DDL** + a **schema doc** for the read-only artifact the engine
  loads: tables for systems, stars (+ `binary`), bodies (+ orbit elements, moons),
  belts, places/stations (`rides_on`), wormhole junctions + links/termini,
  hyperspace bands, hyper-limit table, ship classes, ships, nations — with FK
  relationships, the **id-namespacing** convention (system-qualified ids), and the
  `canon`/`determined`/`valid_from`/`valid_to` columns.
- A throwaway stub that creates an **empty SQLite from the DDL** proves it's valid
  (no compile logic yet).

### Contract 2 — engine OpenAPI — `contracts/engine-openapi.yaml`
- Hand-authored **design-first** OpenAPI (v0.1.0) for the Phase 2 engine surface:
  systems (list/detail), bodies + state across systems, file ship, **file route**
  (multi-mode), ship state galaxy-wide, **junction/queue state**, clock. Endpoints
  need not be implemented this sprint — the spec is the frozen target.
- Validate it lints (an OpenAPI validator).

### Build orchestration
- Root `justfile` recipes spanning the workspace: `engine` check/build/deploy
  (existing behavior, repathed), `contracts` validate (lint OpenAPI + build sample
  artifact), plus a `check` that runs the engine gate. Per-component recipes where
  it helps.

## Out of scope

- Any **new engine behavior** — no multi-system endpoints, no DES core, no
  route execution. (Those are 2a+.)
- Real **universe-compiler** logic (JSON→SQLite) — 2a; here only a DDL + stub.
- **Coordinate frame, orbit derivation** — 2a.
- **UI** beyond a placeholder dir — 2.5.
- **Rust** — not now (the contracts are what make it cheap later).
- **Postgres** — staying SQLite.

## Tasks

- [x] Move `src/hvsim` + `tests` under `engine/`; give `engine/` its own
      `pyproject.toml`; fix `Dockerfile`, `deploy/compose.yaml`, `justfile`,
      entry points, and doc paths.
- [x] Verify Phase 1 intact from the new layout: engine gate green; Docker image
      builds; `just deploy` still serves on kubsdb (redeploy + `just health`).
- [x] Create `tools/`, `contracts/`, `ui/` scaffolding; root `justfile`
      orchestration across the workspace.
- [x] Migrate the dataset into `data/`; add `data/LICENSE` (CC BY-SA 3.0); keep
      `ATTRIBUTION.md`. Relocate scribe skills to `.claude/skills/`.
- [x] Author **Contract 1** (universe-artifact SQL DDL + schema doc, v0.1.0) +
      a stub that builds an empty SQLite from it.
- [x] Author **Contract 2** (engine OpenAPI v0.1.0) + lint it.
- [x] `just contracts` validates both; README/CLAUDE.md updated for the new layout.

## Acceptance criteria

- Repo is laid out as `engine/ tools/ data/ contracts/ ui/` with a root
  `justfile`; **Phase 1 engine builds, tests pass, and the kubsdb deployment
  still works** from the new structure (no behavior change).
- `data/` holds the migrated dataset with its own **CC BY-SA 3.0 `LICENSE`** +
  `ATTRIBUTION.md`; root stays **MIT**. Scribe skills still invocable.
- `contracts/` holds **v0.1.0** universe-artifact schema (DDL + doc) and engine
  OpenAPI; `just contracts` builds a sample empty SQLite from the DDL and lints
  the OpenAPI clean.
- No new engine endpoints/behavior; the validation gate (engine tests + ruff +
  format) is green.

## Notes / decisions

- This sprint deliberately touches the **shipping pipeline** (Dockerfile, deploy
  paths, packaging, the static-asset path, `where-is`). The bar is "Phase 1
  unchanged in behavior, relocated in structure" — verify by redeploying.
- Contracts are **versioned** (`v0.1.0`) and will evolve through 2a–2c; freezing
  them now is what keeps the deferred Rust-port (and the tools/UI seams) cheap.
- Migrating the dataset changes where the data-scribe agent works (in-repo
  `data/` going forward); the JSON-source-of-truth + git review workflow is
  unchanged, just relocated.
- The universe-*compiler* (DDL → populated SQLite from JSON) is 2a; 2.0 only
  fixes the DDL shape so the compiler has a target.

## Outcome — DONE

- Shipped on branch `sprint-009-phase2-contracts`. Monorepo restructured; **Phase
  1 unchanged in behavior and re-verified live on kubsdb** (image builds from
  `engine/`, redeployed, `/health` + map + `/metrics` + 4 persisted ships OK).
- Layout now `engine/ tools/ data/ contracts/ ui/` + root `justfile`. Engine
  moved to `engine/` (own `pyproject`/`uv.lock`/`Dockerfile`/`README`); `just
  check` green (63 tests, ruff/format). `just build`/`deploy` repathed to `engine`.
- Dataset migrated to `data/` (JSON source of truth) with its own **CC BY-SA 3.0
  `LICENSE`** + `ATTRIBUTION.md`; root stays MIT. Scribe skills relocated to
  `.claude/skills/` (still invocable).
- **Contracts frozen at v0.1.0** in `contracts/`: universe-artifact `schema.sql`
  (15 tables, FK-resolved, id-namespaced, `canon`/`valid_*` columns) + `README`;
  engine `engine-openapi.yaml` (13 paths, design-first). `just contracts` builds
  an empty SQLite from the DDL and lints the OpenAPI — both pass.
- No new engine behavior, as scoped. Next: Phase 2a (universe-compiler + frame +
  binary ephemeris) builds on these contracts.
