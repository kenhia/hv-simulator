# Sprint 036 — Dashboard pass (board sort, multi-leg timeline, ship detail finish)

The **remaining** slices of korg proposal **177** ("hv-simulator dashboard pass") —
visible, satisfying UI progress, no engine/routing rework. Sprints 028–034 already
shipped the bulk of 177; this finishes the genuinely-open items.

Proposal: korg **#177** (active). Reconciled: **#57** done (superseded by the
SvelteKit UI's layer toggles + Locate/show-hide + board filter); **#72** / **#78**
partially shipped (031 / 032) — their remaining slices are here.

## In scope

### 1. Fleet Board sort — **#81** (M, UI)
Radio buttons to sort the roster (filters from 032 still apply on top):
- **Transponder code** (default)
- **Full name** (prefix then name)
- **Ship name** (without prefix)
- **Flight-plan file time**, descending (latest filed on top)

Pure `boardSort(roster, mode)` helper (tested) + a compact control in the board
header/filter area. File-time sort needs the filed time — the board's `FleetEntry`
doesn't carry it today; add `filed_at` (route `created_at`) to `GET /fleet` (engine,
small) or sort by a proxy if simpler. Persist the chosen sort in component state.

### 2. Multi-leg Ship Timeline — **#73** (M, UI)
Stacked per-leg strips for multi-destination routes (origin → A → B → …). Factor the
existing `ShipTimeline` per-segment strip into a reusable piece; render one strip per
**leg** (leg boundary = where `to_system`/`body` changes in the route segments),
offset/indented so the sequence reads top-to-bottom; layovers get a dwell marker; the
single progress marker still shows the ship's current leg + position. Single-
destination routes keep the current flat strip. Small render test for the leg split.

### 3. Ship detail finish — **#72 remaining slice** (M, engine + UI)
The 031 rich popup added velocity (real + apparent + band), phase, ETA, destination,
distance, class, nation. Finish it:
- **Current acceleration** — expose accel on `StateOut` (magnitude from the active
  segment's trajectory during `transit` / `hyper_cruise`; null at rest/layover),
  shown in the panel as **g + km/s²**.
- **Last-body-visited distances** — straight-line **from** the last body and **to**
  the destination body (measured to/from the last *body*, not the raw route origin;
  the non-body-start edge case → measure from the initial start until a body is next
  visited). UI-computed from `/fleet/{tp}/state` + body positions; cross-frame care
  on interstellar legs.
- **Current leg + final destination** labels.

### 4. Planet ships-at-rest board — **#78 remaining slice** (S, UI)
Beyond 032's at-planet leader labels: make a body's at-rest ships **openable** —
clicking a planet (or its leader) opens a small panel with a **count** and a
**searchable, read-only list** of the ships at rest there (no checkboxes; click a
row → select/locate that ship). Reuses the 032 `atBodyGroups` grouping.

## Out of scope
- #57 (legacy Sol map panel) — superseded, marked done in korg.
- Repeating routes (#59 / Sprint 035 / korg #185) and wormhole-leg work (#76/#77 /
  korg #186) — separate proposals.
- Relativity `subjective_time_delta` (reserved).

## Tasks
- [ ] #81: `boardSort` helper + test; header radio control; `filed_at` on `/fleet`
      (engine) for the file-time sort.
- [ ] #73: factor per-leg strip; stacked multi-leg timeline; leg-split test.
- [ ] #72: accel on `StateOut` (engine) + test; ship-detail accel + last-body
      distances + current-leg/final labels (UI).
- [ ] #78: openable per-planet ships-at-rest panel (count + searchable list).
- [ ] `just check` (+ `contracts` if `StateOut`/`/fleet` schema changes); docs
      (CLAUDE.md / planning/007); reconcile #72/#73/#78/#81 to resolved on ship.

## Acceptance criteria
- Board sorts by all four modes; filters still apply; default is transponder.
- A multi-destination ship shows a legible stacked timeline; single-dest unchanged.
- Ship detail shows acceleration (g + km/s²) and from/to last-body distances +
  current leg / final destination.
- Clicking a planet with parked ships opens a searchable list of them.
- All gates green; korg #72/#73/#78/#81 resolved, #177 ready to close on ship.
