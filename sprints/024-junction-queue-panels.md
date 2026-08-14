# Sprint 024 — Junction queue panels

Visualize the wormhole transit queue: click a junction nexus → a live board that
shows who's waiting and counts down **#3 → #2 → #1 → pops**. The engine side
(`GET /junctions/{id}/queue`) already exists (Sprint 020); this is its **UI
consumer**, so a lighter, UI-only sprint riding on 022's system scene + 023's live
clock.

Vision: [`sprints/planning/007`](planning/007-ui-vision.md).

## Goal

In a junction-host system, a **nexus marker** is visible; clicking it opens the
**Junction Queue panel** — the junction name + `traffic_intensity`, and the ordered
queue (real ships by transponder + phantom traffic) with **position #**, mass, and
a **transit ETA counting down** as sim time advances. As ships transit they drop
off and the rest move up.

## The data (already served — Sprint 020)

`GET /junctions/{id}/queue?at=<T>` → `JunctionQueue`:
`{ junction_id, when, traffic_intensity, entries: [{ transponder|null, position,
mass_tons, transit_eta }] }` — `transponder == null` is phantom traffic. The queue
is empty unless a real ship is transiting that junction at `T` (phantom only exist
relative to a real arrival). No engine change expected.

## Design

### Opening the panel
- In the **system scene**, draw a **nexus marker** for each junction whose
  `host_system_id` is the current system (from the galaxy `junctions` list).
  Canon gives the nexus a radial distance but not an in-system bearing, so place it
  at a **fabricated** point (`canon:false`) — e.g. just outside the hyper-limit
  ring on a fixed bearing. Click it → open the queue panel for that `junction_id`.
- Secondary (if cheap): when a junction-host system is selected in the **galaxy**
  scene, offer a "view queue" affordance in its data panel.

### JunctionQueue panel (live)
- Polls `GET /junctions/{id}/queue?at=simNow` every ~3-5s for the entry set, and
  recomputes the **`transit in MM:SS`** text each second locally from
  `transit_eta − simNow()` (the 023 sim clock) so the countdown is smooth.
- Rows: `#position · transponder|"(phantom)" · transit in MM:SS` (+ mass on hover/
  detail). Header: junction name + `traffic_intensity`. Empty state: "no transits
  queued" (junction idle at this time).
- Dismissable, like the Side Data Panel. Reuses the live clock from the page.

### Countdown helper (pure, testable)
- `etaText(transit_eta_ms, sim_now_ms)` → `#`-free `MM:SS` (or `HH:MM:SS`), clamped
  at 0 ("transiting"). Unit-tested, like `camera`/`live`.

## Scope

1. `api.ts`: `JunctionQueue` / `JunctionQueueEntry` types + `fetchJunctionQueue(id,
   at?)`.
2. Nexus marker in `SystemMap` for host-system junctions (fabricated position) +
   click → `onjunction(id)`.
3. `JunctionQueuePanel.svelte`: poll + local per-second countdown; ordered rows;
   empty state; uses the page's `simNow`.
4. Page wiring: open/close the panel; pass `simNow` from the LiveFleet clock.
5. Pure `etaText` helper + Vitest.
6. `just check` (engine + UI) + `just contracts` green; deploy + demo.

## Out of scope (later)

- **Rich ship popup** (velocity/band/accel/distances) — KWI #72.
- **Binary star geometry** (#69), **label click-targets** (#70), **scale bar**
  (#71) — filed, independent.
- **Faction colours, main menu, dev time scrubber** — 025.
- **Mass-transit / emergency-buffer queue modes** — engine-side, later.

## Tasks

- [ ] `api.ts` queue types + `fetchJunctionQueue`.
- [ ] Nexus marker (host-system junctions) in `SystemMap`; click → `onjunction(id)`.
- [ ] `JunctionQueuePanel.svelte` (poll + per-second countdown, rows, empty state).
- [ ] `etaText` pure helper + Vitest.
- [ ] Page wiring (open from nexus; pass `simNow`); optional galaxy affordance.
- [ ] `just check` + `just contracts` green; deploy + demo (route a ship through
      the Manticore Junction, watch the board count down).

## Acceptance criteria

- Clicking a junction nexus in its host system opens a panel listing the live queue
  (real ships + phantom) with positions + transit ETAs; the ETA **counts down** as
  sim time advances and entries drop off as they transit.
- The panel reads the junction's `traffic_intensity`; an idle junction shows an
  empty state.
- `just check` (engine + UI) + `just contracts` green; deployed + demoed on kubsdb.

## Notes / decisions

- **UI-only** — `GET /junctions/{id}/queue` already exists (020); no engine change
  anticipated. Smaller than 023.
- The nexus in-system position is **fabricated** (canon gives radius, not bearing);
  flag `canon:false`, consistent with the galactic frame + binary geometry notes.
- The countdown uses the **shared sim clock** (023), so dev fast-forward drives the
  board too — the `#3 → pops` demo works at accelerated rate.
- Closes the Phase-2c loop visually: the queue resolver (019) → deployed endpoint +
  metrics (020) → **the board a user actually watches** (024).
