# Sprint 011 — Complete Phase 2a: galactic frame + route graph + hyperspace

The rest of **Phase 2a** (the items 010 deferred). Makes the **universe artifact
complete and the galaxy navigable-on-paper**: systems placed in a fabricated
galactic frame, the wormhole route graph + transit model compiled in, and the
hyperspace band / hyper-limit model available. Still **no travel** — the DES core
and multi-mode flight plans are Phase 2b.

## Goal

After this sprint the engine can load a universe artifact that knows *where
systems are* (3D), *how they connect* (wormhole links + junction queue model),
and *the hyperspace rules* (bands + per-star hyper limits) — everything 2b's
travel will consume. Inter-system distances are answerable (canon pairwise where
known, frame-derived otherwise).

## Scope

### `tools/coordinate-frame/` (own `pyproject.toml`)
- A fabricated **Sol-origin, +Z galactic-north** frame. Place each *built* system
  from its `location` (`distance_ly` + `direction` + `reference`), resolving
  reference chains (Sol → Manticore → …), via a documented direction→unit-vector
  map (e.g. "galactic north" → +Z; "NE"/etc. → fabricated bearings). Write a
  `coordinates` block into `data/systems/*.json` (`canon:false`). Unbuilt terminus
  systems get coords when they're built. Deterministic; flagged fabrication, like
  the orbits.

### `universe-compiler` extensions
- `star_systems.coord_x/y/z_ly` (+ `coord_canon=0`) from the frame.
- **hyperspace**: `hyperspace_bands` from `bands[]`; `hyper_limits` from
  `hyper_limit.by_spectral_class` (full O–M table); compute each star's
  `hyper_limit_lmin` by spectral-class lookup (exact like `G0`, first-letter
  fallback).
- **wormholes**: `wormhole_junctions` (id, name, host system) and
  `wormhole_links` (endpoints → from/to system, via-junction, `distance_ly`,
  transit) and `transit_model` (coeffs + safety buffers).
- Extend FK **stubbing** to systems referenced by wormhole endpoints / junction
  hosts (Beowulf/Trevor's Star/etc. are unbuilt).

### Engine
- Load the new tables. Expose:
  - `GET /systems` includes `coordinates` (+ existing fields).
  - `GET /wormholes` (links) and `GET /junctions` (with host).
  - `inter_system_distance(a, b)`: **canon pairwise** wormhole-link distance if
    directly linked, else **frame** Euclidean from coordinates. (Engine function
    + a `GET /systems/{a}/distance/{b}` convenience.)
- A galaxy-map data surface only — **no route execution / travel** this sprint.

### Orchestration & docs
- `justfile`: a `frame` recipe (run coordinate-frame); fold into `compile-data`'s
  inputs (frame is run like `derive-orbits` — once, committed). Extend `check`
  with the new tool's tests. README/CLAUDE: the frame's fabricated nature + the
  completed artifact contents.

## Out of scope (Phase 2b)

- **DES core**, route execution, multi-mode flight plans (n-space→hyper→wormhole),
  the wormhole **queue resolver** + phantom traffic. No ship *moves* yet.
- Coordinate-frame precision beyond the heuristic (canon is qualitative).
- UI (2.5); Sol into the dataset (stays special-case).

## Tasks

- [x] `tools/coordinate-frame`: place built systems (Sol-origin, +Z north) from
      distance+direction+reference; write `coordinates` (canon:false) to data/.
- [x] Compiler: compile coords, hyperspace bands, hyper-limits (+ per-star),
      wormhole junctions/links, transit model; extend stubbing to wormhole refs.
- [x] Engine: load + expose `/systems` (coords), `/wormholes`, `/junctions`, and
      `inter_system_distance` (canon pairwise else frame) + a distance endpoint.
- [x] `justfile` `frame` recipe; extend `check`; rebuild `build/universe.db`.
- [x] Tests: frame placement (Manticore ~+512 ly Z), compiler (bands=10,
      hyper-limits populated, 2 junctions / 12 links, per-star hyper limit),
      engine distance (canon pairwise vs frame) + endpoints; Sol unchanged.
- [x] README/CLAUDE updates.

## Acceptance criteria

- `tools/coordinate-frame` places the 4 built systems in the frame (Manticore at
  ~+512 ly on +Z), written `canon:false` to `data/` and compiled into
  `star_systems.coord_*`.
- The artifact is **complete**: `hyperspace_bands` (10), `hyper_limits` (full
  class table), each star's `hyper_limit_lmin` set, `wormhole_junctions` (2) +
  `wormhole_links` (12) + `transit_model`; wormhole-referenced unbuilt systems
  are stubbed so FKs hold.
- Engine exposes `/systems` (with coordinates), `/wormholes`, `/junctions`, and an
  inter-system distance that returns the canon link distance when two systems are
  directly wormhole-linked (e.g. Manticore↔Basilisk = 210 ly) and a frame-derived
  distance otherwise.
- **No travel/route endpoints** added. Sol unchanged; `just check` green (engine +
  tools); contract still **v0.1.0** (all columns already exist).

## Notes / decisions

- The frame is fabrication over qualitative canon bearings — first-pass and
  flagged `canon:false`, refine/hand-tune later (same posture as orbit-derive).
- `inter_system_distance` prefers canon pairwise (wormhole link `distance_ly`)
  because those are real; frame Euclidean is the fallback for the general case
  (per `006`/`004`).
- Contract unchanged (v0.1.0 already has coord/wormhole/hyperspace tables — 009
  designed them ahead). This sprint *populates* them.
- After 011, Phase 2a is complete and 2b (DES + travel) has a full universe to
  fly through.

## Outcome — DONE

- Shipped on branch `sprint-011-complete-phase2a`. `just check` green: engine
  (69 tests) + all three tools; ruff/format clean. Sol unchanged.
- **`tools/coordinate-frame`**: Sol-origin, +Z-galactic-north frame; placed the 4
  built systems from distance+bearing+reference chains (Manticore +512 ly Z;
  Manticore↔Yeltsin's ≈ 31 ly, matching canon). Coords written `canon:false` to
  `data/`.
- **Compiler** now fills the rest of the artifact: system coordinates, hyperspace
  bands (10) + hyper-limit table (44 classes) + per-star `hyper_limit_lmin`,
  wormhole junctions (2) + links (12) + transit model. Stubbing extended to
  wormhole-referenced systems (now 13 systems: 4 built + 9 stubbed termini).
- **Contract bumped to v0.1.1**: `wormhole_links.to_system_id` made nullable
  (two canon Erewhon termini point to as-yet-unidentified Solarian systems).
- **Engine**: `/systems` includes coordinates; new `/wormholes`, `/junctions`,
  and `/systems/{a}/distance/{b}` (verified Manticore↔Basilisk = 210 ly canon,
  Sol↔Manticore = 512 ly frame). `inter_system_distance` prefers canon link span,
  falls back to frame.
- **Phase 2a is complete.** Deferred to 2b (as scoped): the DES core, route
  execution, multi-mode travel, wormhole queues. The universe is now fully
  loadable; nothing flies yet.
