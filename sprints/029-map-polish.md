# Sprint 029 — Map polish (legible & smooth)

Four UI polish items that make the maps legible and the interaction smooth in a
live demo. All client-side — the engine already serves the data each needs.

Plan: [`planning/007`](../planning/007-ui-vision.md) · KWIs #71 / #74 / #75 / #70.
Second sprint of the demo-first arc (028 made the maps *look right*; 029 makes them
*read right*).

## Goal

- A **scale bar** so distances are legible, auto-picking the unit for the zoom
  (ly at galaxy scale; AU / light-minutes / light-seconds inside a system).
- **Wormhole-terminus markers** in non-host systems (Basilisk, Trevor's Star, …)
  so a user there can see and click the wormhole back to the junction.
- **Queued ships drawn at the nexus**, not stacked on the system's star.
- **Clickable labels** — hit-testing covers each node's text, not just its dot.

## #71 — Adaptive scale bar

The camera knows `scale` = pixels per world-unit (**ly** in the galaxy scene, **AU**
in the system scene; [camera.ts](../ui/src/lib/camera.ts)). A new pure helper keeps
it testable, like `camera.ts` / `planner.ts`:

- `scaleBar(scale: number, baseUnit: 'ly' | 'au', targetPx = ~90): { pixels, label }`
  1. world-distance = `targetPx / scale` in the base unit.
  2. Convert to a display unit by magnitude and snap to a "nice" 1/2/5×10ⁿ number:
     - galaxy (**ly**): light-years.
     - system (**au**): AU → **light-minutes** → **light-seconds** as you zoom in
       (1 AU = 8.317 lmin = 499 ls); **km** at the tightest zoom.
  3. return the bar's pixel length + label (e.g. `5 AU`, `30 light-min`, `2 ly`).
- Render a labelled bar bottom-centre (or bottom-left) in both `GalaxyMap` and
  `SystemMap`; pass the scene's base unit in. Thresholds chosen so the number stays
  in a readable 1–3 digit range and transitions feel natural.
- Constants from the engine: 1 AU = 1.495978707e11 m, 1 light-minute = 1.798754748e10 m,
  1 ly = 9.4607304725808e15 m.

Tests: `scaleBar` unit ladder + nice-number snapping (a few representative scales
per scene).

## #74 — Wormhole-terminus markers in non-host systems

`SystemMap` draws a nexus glyph only for junctions whose `host_system_id ==
systemId` (Manticore). Terminus systems host no junction, so their view shows
nothing. The data is already there — `/wormholes` returns `to_terminus_name` (add
it to the `WormholeLink` type in [api.ts](../ui/src/lib/api.ts); no engine change).

- Draw a **terminus marker** for links landing in the current system: a true
  wormhole (`transit === 'instant'`) where `to_system_id === systemId` (and/or
  `from_system_id === systemId` for the reverse direction).
- Fabricated in-system position (`canon:false`, like the host nexus — canon gives a
  radius not a bearing; reuse the `nexusWorld`-style placement and include it in
  the fit).
- Label it with where it leads + its junction (e.g. `⇄ Manticore Junction`, from
  `junction_id`); **clickable → that junction's queue panel** (reuse 024's
  `JunctionQueuePanel` with the link's `junction_id` — a terminus shares the host
  junction's queue).
- Distinct glyph from the host nexus (e.g. paired-arrow `⇄` vs the host ring `⚲`)
  so "I host the junction" vs "I'm a terminus to it" reads clearly.

## #75 — Draw queued/transiting ships at the nexus

A ship in phase `queued` / `wormhole_transit` reports its position as the
from-system star centre (the queue segment's position is immaterial), so the live
dot lands on the star — it reads as "parked on the star," not "waiting at the
junction."

- In `SystemMap.drawShips`, when a tracked ship's phase is `queued` /
  `wormhole_transit` and it's in the current system, draw it **at (or just beside)
  that system's nexus/terminus marker** instead of its raw heliocentric position.
- Use the same fabricated nexus point the markers use; optionally annotate the dot
  with its `queue_position` (`#N`). Pure UI placement — no engine change.
- (The deeper "fly to the nexus first" is the engine item #76, deferred.)

## #70 — Clickable labels

Hit-testing (`nearest`) covers only the node **dot** (~14 px). Extend it to each
node's **label bounding box** (measure with `ctx.measureText`, build a rect from the
label's draw position + font height) so a click on the name selects the node too.

- Applies to `GalaxyMap` and `SystemMap`; factor a small shared helper
  (`labelHit(cursor, anchorScreen, text, ctx)` → boolean) so both use one impl.
- Keep the existing small-radius dot hit (labels overlap when zoomed out; the dot
  stays the precise target).

## Tasks

- [ ] `ui/lib/scalebar.ts` — pure `scaleBar()` + unit ladder; `scalebar.test.ts`.
- [ ] Render the scale bar in `GalaxyMap` (ly) and `SystemMap` (au).
- [ ] `api.ts`: add `to_terminus_name` to `WormholeLink`.
- [ ] `SystemMap`: terminus markers (position + label + click → `JunctionQueuePanel`),
      included in fit; distinct glyph from the host nexus.
- [ ] `SystemMap.drawShips`: place `queued`/`wormhole_transit` ships at the nexus
      (+ optional `#N`).
- [ ] Label hit-testing in both maps (shared `labelHit` helper) + a small test.
- [ ] `just check` green (engine unchanged; UI vitest + svelte-check + prettier).

## Acceptance criteria

- A labelled scale bar shows on both scenes and changes unit/number sensibly across
  the full zoom range (ly ↔ AU ↔ light-min ↔ light-sec ↔ km).
- Basilisk / Trevor's Star / Sigma Draconis system views show a clickable terminus
  marker that opens the Manticore Junction queue panel.
- A queued ship renders at the junction nexus, not on the star.
- Clicking a system/body **name** selects it (not just the dot).
- All gates green.

## Out of scope (deferred)

- Engine "fly to the nexus, rest, then queue" (#76) and distinct-terminus model
  (#77) — both deferred behind the light-second-sphere simplification.
- Rich ship popup (#72), multi-leg timeline (#73) — later.
- Per-star hyper-limit rings / animated binary orbit (028 out-of-scope).
