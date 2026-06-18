# Sprint 031 — Demo polish (board glyphs, rich ship detail, locate)

Three small, high-payoff tweaks for the demo. (Repeating routes — the old 031 —
moved to **032**.)

Plan: [`planning/007`](../planning/007-ui-vision.md). Touches `ui/` + a small engine
state addition. Builds on the Observer (023–025) and the rich-popup brainstorm #72.

## Goal

- **Fleet Board** rows show the **full ship name** — replace the truncating
  `phase + ETA` columns with a single **phase glyph** before the name:
  `[✓] <transponder> <glyph> <ship name>`.
- **Ship detail** gets richer: the phase/ETA we removed from the board, plus
  destination, progress, distances, and **velocity** — real, and in hyper the
  **apparent velocity + band** (engine-exposed). A chunk of #72.
- **Locate ship** button on the ship detail: centre the camera on the ship at a
  set zoom — **LOD-aware** so interstellar ships frame on the galaxy scene instead
  of vanishing when you drill in.

## Part 1 — Fleet Board glyph reformat (UI)

[`FleetBoard.svelte`](../ui/src/lib/FleetBoard.svelte) row is today
`[✓] <tp> <name (truncated)> <phase> <eta>`. Change to:

```
[✓] <transponder>  <phase-glyph>  <ship name>
```

- Drop the `.ph` (phase/queue text) and `.eta` columns; give `.nm` the freed width
  (still ellipsis as a backstop, but names now fit).
- A **phase → glyph** map (monochrome, monospace-safe), reusing the ShipTimeline
  segment glyphs where possible for consistency. Proposed:
  - `predeparture` / `idle` ○ · `transit` ▸ · `hyper_cruise` ✦ · `layover` ‖ ·
    `queued` ⧖ (or `#N` when a queue position is set) · `wormhole_transit` ⊚ ·
    `arrived` ●
  - Tooltip (`title`) on the glyph spells out the phase (so the legend isn't lost).
- Keep the inline ShipTimeline + itinerary on the selected row (unchanged).

## Part 2 — Richer ship detail (engine + UI)

### Engine — expose hyper band + apparent velocity (part of #72)
`StateOut` has only *real* velocity. Add, meaningful during `hyper_cruise`:
- **`band`** — the current hyperspace band (order + name, e.g. `{order: 6, name:
  "Zeta"}`); null outside hyper.
- **apparent velocity** — `apparent = velocity_multiplier(band) × real_cruise`.
  Extend `VelocityOut` with `apparent_fraction_c` / `apparent_speed_km_s` (null
  outside hyper), or add an `apparent` sub-object. Source from the active
  `hyper_cruise` segment + the artifact band table (the data already drives this in
  `route/`).
- (Optional, if cheap) **current acceleration** (g + km/s²) from the active
  segment's trajectory — nice for the brachistochrone/accel phases. Defer if it
  adds risk.
- Keep it null/absent for non-hyper phases; no change to existing fields. Bump the
  OpenAPI contract if the schema changes (additive).

### UI — the detail panel
Selecting a ship currently builds rows from the lightweight `FleetEntry`
(`shipRows`). Fetch `/fleet/{tp}/state` and render a richer panel:
- **phase** + **ETA** (moved from the board) · **destination** · **% complete**.
- **velocity**: `0.382c` in n-space; in hyper `0.382c real · 1640c apparent (Zeta)`.
- **distance to destination** (already on state as `distance_to_destination_km`),
  shown in a sensible unit (AU/ly).
- **system / frame** + **transponder / class / nation** (from the catalog).
- Keep it resilient: if `/state` fails, fall back to the basic rows.

(Full #72 — last-body distances, current-leg vs final, accel always — stays open;
this sprint does the board-removal items + band/apparent velocity.)

## Part 3 — Locate ship (UI + camera)

Add a **Locate** button to the ship detail panel. Add a camera helper
`centerOn(world, scale, width, height)` (sibling to `fit`) → a `Camera` centred on
`world` at a chosen `scale`. Behaviour keys on the ship's live frame:
- **Interstellar** (frame `galactic`, e.g. a `hyper_cruise` ship): ensure the
  **galaxy scene** is active, centre on the ship's galactic position (km→ly, X-Z)
  at a close galaxy zoom, and engage a **galaxy follow-lock** (`lockGalaxy`) so
  zooming in keeps tracking the ship on the galaxy scene instead of drilling into
  the host system (where galactic-frame ships aren't drawn). The lock is the galaxy
  analogue of the system **zone-lock**: toggle with `z`, release with `Esc` (which
  re-frames the galaxy). The galaxy scale bar steps down to **light-hours / minutes**
  on a deep locked zoom so the readout stays sensible. **This is the full fix for
  the "zoomed in and lost my ship" case** — you can follow a ship out of its home
  zone and watch it fly interstellar.
- **In-system** (frame `heliocentric`): enter that system (if not already there),
  centre on the ship's heliocentric position (km→AU) at a fixed system zoom.
- Ensure the ship is **tracked/visible** (locate implies show) and selected.
- Re-centre off the live position at click time (dead-reckoned); no continuous
  follow (a one-shot framing is enough and avoids a moving-camera fight with pan).

## Tasks

- [ ] FleetBoard: phase-glyph map + row reformat (drop phase/eta cols, widen name,
      glyph tooltip); update `scene`/board tests if row structure is asserted.
- [ ] Engine: `band` + apparent velocity on `StateOut`/`VelocityOut` during hyper;
      unit test (a hyper-cruise state reports band + apparent = mult × real); UI
      `api.ts` types updated; `just contracts` if schema changed.
- [ ] UI ship detail: fetch `/fleet/{tp}/state`, render the rich rows (incl.
      apparent/band in hyper), graceful fallback.
- [ ] `camera.ts` `centerOn` + test; Locate button wired LOD-aware (galaxy vs
      system), ship tracked+selected+centred.
- [ ] `just check` green (engine pytest + ruff + UI vitest + svelte-check).

## Acceptance criteria

- Fleet Board rows show full ship names with a leading phase glyph; no phase/eta
  text columns; glyph tooltip names the phase.
- Ship detail shows phase, ETA, destination, %, distance, and velocity — with
  apparent velocity + band while a ship is in hyper.
- Locate centres any ship in one click: an interstellar ship (e.g. PNS Sultan
  618.1.3 mid-hyper) frames on the galaxy scene and stays visible; an in-system
  ship frames within its system.
- All gates green.

## Out of scope (deferred)

- Repeating routes (#59) — Sprint 032.
- The rest of #72 (last-body distances, current-leg vs final, always-on accel) and
  the multi-leg timeline (#73).
- Continuous camera follow (one-shot locate only).
