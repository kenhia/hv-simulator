# Sprint 028 — Map fidelity (binary geometry + galactic spread)

Make the maps *look right*. Two fixes that together remove the most jarring
visual problems in a live demo:

- **#69** — binary systems (Manticore) render with one star at the origin and
  planets "scattered" around an empty point. Draw **each star at its real offset**
  and group planets by their parent star.
- **#68** — the galaxy renders as a near-vertical **line**: every system whose
  canon bearing is "galactic north" maps to the same axis (X = 0), so Sol, Sigma
  Draconis, Manticore, Basilisk all stack. Spread them with a deterministic
  **bearing-arc** jitter.

Plan: [`planning/007`](../planning/007-ui-vision.md) · KWIs
[#69](.) / [#68](.). First sprint of the **demo-first** post-027 arc.

## Goal

Open the galaxy map → systems are spread across a believable wedge, not a column.
Drill into Manticore → two labelled stars sit at their barycenter offsets, each
with its planets visibly orbiting it. No new physics — the engine already computes
both; this exposes and draws them, plus one deterministic tweak to the frame tool.

## Part A — Binary star geometry (#69)

### The data
The engine **already computes** per-star offsets: `star_positions(u, system_id,
when)` ([engine/src/hvsim/universe/__init__.py](../engine/src/hvsim/universe/__init__.py))
places each star from the `binaries` row (`barycenter_a_lmin` / `_b_lmin`,
eccentricity) around the barycenter origin, and `body_positions` already bases each
planet on its `parent_star_id`'s offset. The gap is purely **exposure + drawing**:
`GET /systems/{id}` returns the `stars` list and `binary` row but **no per-star
XYZ**, and `SystemMap` draws the primary at the origin.

Manticore (canon, already in the artifact): A at 333 lmin ≈ 40.1 AU, B at 406 lmin
≈ 48.8 AU on the opposite side; mean separation ≈ 88.9 AU. The **only** fabricated
bit is the A–B axis orientation/phase (canon gives distances, not where in the
orbit) — place along a deterministic axis at the mean separation, `canon:false`.
`orbital_period_days` is null, so a **static** placement is fine for v1.

### Engine
- Add each star's in-system position (AU, same frame as `/systems/{id}/bodies`) to
  the `GET /systems/{id}` response — `StarOut.position` (reuse `PositionOut`), or a
  sibling `star_positions` field. Single-star systems → the one star at origin.
- Source it from `star_positions` (add a deterministic A–B axis if not already
  fixed). No change to `body_positions` (already parent-relative).

### UI (`SystemMap.svelte`)
- Draw **each star** at its offset (screen = `worldToScreen(star.position)`),
  labelled (A / B with names), distinct from planet glyphs.
- Group/colour planets by `parent_star_id` so each star owns its little system.
- Hyper-limit ring: keep per-primary for v1 (per-star is a later nicety); ensure
  the ring centres on the primary's drawn position, not the origin.
- Fit: include both stars in the auto-fit extent so the pair + planets all show.

## Part B — Bearing-arc galactic spread (#68)

### The frame tool (`tools/coordinate-frame`)
- Today `_direction_unit` maps each compass word to one exact axis
  ([coordinate_frame/__init__.py:18-36](../tools/coordinate-frame/coordinate_frame/__init__.py#L18-L36)).
  Add a **deterministic per-system jitter** within **±22.5°** of the bearing,
  rotating the placement within the X–Z plane (Y stays reserved ≈ 0):
  - `jitter = f(hash(system_id))` mapped into `[-22.5°, +22.5°]` — reproducible,
    hand-tunable, **never random per run**.
  - Position = `distance · unit(bearing rotated by jitter)`.
- Keep it `canon:false`; document the artistic-license rule in the tool docstring.
- Intercardinals (NE/NW) already spread; the jitter mainly de-collinearises the
  pure cardinals. (Out-of-plane Y "disk thickness" from #68's addendum is **out of
  scope** — it only benefits the future 3D viewer; the 2D map ignores Y.)

### Regenerate the artifact
- Re-run the pipeline: `just frame` → `just compile-data` → `build/universe.db`
  (the engine reads coords from the artifact). Galaxy map then shows the spread.
- Sanity: Sol stays at origin; no two placed systems share X=0 anymore; distances
  (the canon bearing magnitude) are preserved — only the direction is jittered.

## Tasks

- [ ] Engine: expose per-star in-system positions on `GET /systems/{id}` (+ schema).
- [ ] Engine: ensure `star_positions` has a deterministic A–B axis; unit test the
      Manticore offsets (~40.1 / ~48.8 AU, opposite sides).
- [ ] `tools/coordinate-frame`: deterministic ±22.5° bearing-arc jitter + test
      (same seed ⇒ same coords; distance preserved; pure-cardinal systems get X≠0).
- [ ] Regenerate `build/universe.db` (`just frame` + `just compile-data`).
- [ ] UI `SystemMap`: draw both stars at offsets, group planets by parent star,
      fit both stars; ring centres on the primary.
- [ ] UI: a small test for the parent-star grouping / star-placement helper.
- [ ] `just check` green (engine pytest + ruff + UI vitest + svelte-check);
      `just contracts` if the system-detail schema changed.
- [ ] `docs/galaxy-changelog.md` note if the regenerated coords shift placements.

## Acceptance criteria

- Galaxy map: placed systems are spread across a wedge — **no vertical X=0 stack**;
  re-running the frame tool yields identical coordinates (deterministic).
- Manticore system view: **two labelled stars** at their barycenter offsets, each
  with its planets clustered around it; auto-fit shows the whole pair.
- Single-star systems (Sol) unchanged.
- Distances/bearings stay canon-faithful (only intra-bearing direction jittered).
- All gates green.

## Out of scope (deferred)

- Per-star hyper-limit rings; animated binary orbit (static placement for v1).
- Out-of-plane Y disk-thickness (#68 addendum — 3D-viewer only).
- Termini markers (#74), scale bar (#71), queued-at-nexus (#75), label clicks
  (#70) — these are **Sprint 029** (map polish).
