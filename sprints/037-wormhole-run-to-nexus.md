# Sprint 037 — Wormhole leg: run to the nexus before queuing

Fix the "teleport to the queue" behavior: a ship filing a route through a wormhole
junction jumps straight to `queued` at the junction on submit, with **no in-system
travel to the nexus**. It should fly n-space out to the junction nexus (~7 light-
hours), come to rest there, *then* queue + transit. KWI **#76** (korg #186).

Reproduced live: RMMS Atlas `manticore:manticore → basilisk:medusa → manticore:sphinx`
queued instantly on submit (comment on #76). #77 (per-terminus queues) is **deferred**
out of this sprint — the single-nexus simplification stays.

## Root cause

`compile_route`'s `WORMHOLE` branch emits the `wormhole_queue` (+ `wormhole_transit`)
at `when` = the ship's current position, with no travel. Junctions also carry **no
nexus position** (the `wormhole_junctions` table is id/name/host/traffic/canon only),
and the UI *fabricates* the nexus marker (`NEXUS_AU = 50`, bearing = host-index ×0.7).

## Design

Give each junction a **nexus position** in its host system, source it in the engine,
and insert an n-space run to it before the queue. One shared position ⇒ the ship
flies to exactly where the UI draws the nexus.

### 1. Data + contract — nexus location on the junction
- Add to `wormhole_junctions`: **`nexus_dist_lmin`** (radial distance from the host
  primary; canon for Manticore = **420 lmin ≈ 7 light-hours**, fabricated default
  otherwise) + a fabricated **`nexus_bearing_deg`** (canon:false, deterministic —
  e.g. per-junction hash, like the galactic frame). Additive DDL (contract minor
  bump); compiler reads them from `data/wormholes/wormhole-network.json`.
- The in-system nexus point = `dist · unit(bearing)` in the host system's
  heliocentric frame (Y≈0, like other in-system placement). `canon:false`.

### 2. Engine — run to the nexus + report it
- `Universe.junction_nexus_position(junction_id, when?) -> Vec3` (host-system
  heliocentric metres). Shared accessor (the "expose the nexus position" note on #76).
- `compile_route` WORMHOLE branch: **before** the `wormhole_queue`, insert a
  `transit` (brachistochrone, same `Trajectory.between`/solver as run-out) from the
  ship's current in-system `pos` to the nexus point — **unless already at the nexus**
  (a straight-through transit from another terminus arrives there; dist < ε → skip).
  The queue's `t_start` becomes the run-out arrival, not departure.
- The `wormhole_queue` segment now **reports the nexus position** (carry it on the
  Segment; `des/model.py` returns it instead of `ZERO`/star-centre) — so a queued
  ship sits at the nexus in its real heliocentric frame. This supersedes #75's UI
  fabrication for the queued phase.

### 3. API + UI — one consistent nexus
- Expose the nexus position on `GET /junctions` (and/or `/systems/{id}`) so the UI
  draws the marker at the engine's point instead of the fabricated `NEXUS_AU`/bearing.
- `SystemMap`: nexus marker uses the exposed position; queued/`wormhole_transit`
  ships render at their reported (now real nexus) position — the #75 special-case
  can lean on the engine value.

## Tasks
- [x] Data + DDL: `nexus_dist_lmin` + `nexus_bearing_deg` on junctions (Manticore
      420 lmin canon; others fabricated); compiler loads them; `just contracts`.
- [x] Engine: `junction_nexus_position` accessor; `compile_route` run-to-nexus
      transit (skip if already there); `wormhole_queue` carries + reports the nexus
      position (`Segment` + `des/model.py`).
- [x] Engine tests: a same-system→wormhole route now **starts with a `transit`**
      (run-out) then `wormhole_queue` (not an immediate queue); run-out duration is
      realistic (~a day for 7 light-hours); a straight-through transit skips the run.
- [x] API: nexus position on `/junctions` (+ schema); UI consumes it for the marker
      + queued-ship placement; `api.ts` types.
- [x] `just check` + `contracts` green; docs (CLAUDE.md/planning, galaxy-changelog
      — artifact schema bumped to v0.5.0); korg #76/#186 reconciled at ship time.

## Acceptance criteria
- A route through a junction (e.g. Atlas from `manticore:manticore`) **flies out to
  the nexus first** (a visible ~day-long in-system transit), rests, then reports
  `queued` — no instant teleport.
- The queued ship sits at the nexus in the map (engine-reported position), and the
  nexus marker + the ship agree (one shared position).
- A ship transiting straight through the junction (arriving from another terminus)
  does not re-run to the nexus.
- Determinism/no-loop preserved; all gates green; #76 resolved (#186 closes).

## Out of scope (deferred)
- #77 — per-terminus distinct entry points/vectors + per-terminus queues (stays one
  nexus, one queue; unrelated from #186).
- Band-climb / translation modelling; arrival-vector constraints.
