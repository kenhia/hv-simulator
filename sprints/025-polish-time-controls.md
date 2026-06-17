# Sprint 025 — Polish + dev time controls (Observer finish)

The last of the Observer slice: make the live view *operable and legible* — a
**dev time scrubber** (fast-forward a multi-day trip into seconds, right in the
UI), **faction colours**, **layer toggles**, and a **help overlay** wiring the
reserved keymap. Plus a couple of cheap polish wins. After this, Observer is
"done"; the Controller (Flight Planner) is the next phase.

Vision: [`planning/007`](../planning/007-ui-vision.md). Builds on 023's sim clock
+ live loop.

## Scope is tiered (polish balloons — trim at review)

### Tier 1 — the marquee + core polish
1. **Dev time scrubber** (the headline). A bottom control, shown **only when
   `/clock` reports `dev_controls_enabled`** (hidden in prod). Drives `PUT /clock`:
   - **play/pause** (`Space`) — pause = `rate 0`; play = the selected rate.
   - **rate presets** — 1× / 60× / 3600× / 86400× (real-time → a day/second).
   - **step** (`,` / `.`) — `advance_seconds` back/forward by a sensible grain.
   - **jump to now** — re-anchor. After any change, force an immediate `/clock`
     re-sync so the live view (LiveFleet, queue panel) tracks it.
   - **Engine tweak:** `ClockUpdate.rate` is currently `gt=0`; allow **`ge=0`**
     so `rate 0` freezes the clock (pause). Small + tested.
2. **Faction colours** — colour ship motes/labels (and optionally system nodes by
   controlling nation) from the transponder's **nation code**, via a default
   palette (Manticore, Haven, Grayson, Sol/Solarian, Beowulf, unaffiliated, …).
   User-remappable schemes are deferred (007); v1 is a fixed palette.
3. **Help overlay** (`?`) — render the `keymap` table (it was built as the single
   source of truth for exactly this). Add the `?` binding; activate the reserved
   keys this sprint wires.
4. **Layer toggles** (`l`) — a small control to show/hide: ships, labels, wormhole
   edges, hyper-limit ring, stations. Maps read the layer flags.

### Tier 2 — nice-to-haves (do if time)
5. **Ship itinerary detail** — a leg list (origin → … → destination) in the ship
   panel, alongside the 023 Ship Timeline.
6. **Leader-line de-collision** — nudge overlapping transponder labels on the map
   (best-effort, not a full layout solver).

### Opt-in (cheap filed KWIs that fit the theme)
- **#70** — label as click-target (both maps).
- **#71** — adaptive scale bar (the ruler ladder).
  Pull either/both in if we want; otherwise they stay filed.

## Out of scope (separate)

- **#72 rich ship popup** (effective/apparent velocity + band, accel, distances) —
  needs engine exposure (band + accel on `StateOut`); its own item.
- **#69 binary star geometry** — bigger; stays filed.
- **Controller / Flight Planner**, **main menu (`m`)**, **3D galaxy viewer**,
  **Grafana dashboards** — later / parallel.

## Design notes

- **Time scrubber = server-clock control.** It mutates the shared SimClock (one
  homelab user), dev-gated so prod hides it. The LiveFleet already models the
  clock; the scrubber PUTs then forces a re-poll. `rate 0` = frozen (engine tweak).
- **Faction palette** keyed on the nation code (first transponder component;
  `data/transponder-codes.json`). Keep the mapping in one UI module so the future
  user-remap (007) has a single seam.
- **Help/layers/scrubber** are chrome over existing data — no new fetches beyond
  `PUT /clock`. Keep them behind small components; the keymap stays the source of
  truth for shortcuts.

## Tasks

- [ ] Engine: `ClockUpdate.rate` `ge=0` (allow pause) + test.
- [ ] Time scrubber component (dev-gated): play/pause/rate/step/jump → `PUT /clock`
      + force clock re-sync; wire `Space` / `,` / `.`.
- [ ] Faction colour module (nation → colour) + apply to ship motes/labels.
- [ ] Help overlay (`?`) rendering the keymap; activate the wired keys.
- [ ] Layer toggles (`l`) + maps honour the flags.
- [ ] (Tier 2) ship itinerary leg list; leader-line de-collision.
- [ ] (Opt-in) #70 label clicks and/or #71 scale bar.
- [ ] Vitest for any pure logic (rate/step math, faction lookup); engine test for
      `rate 0`; `just check` + `just contracts` green; deploy + demo.

## Acceptance criteria

- In dev, the time scrubber fast-forwards the live view (ships visibly move,
  queues count down) and pauses; it is **absent in prod** (`dev_controls_enabled`
  false). `rate 0` is accepted by the engine.
- Ships are coloured by faction; `?` shows the shortcut list; `l` toggles layers.
- `just check` (engine + UI) + `just contracts` green; deployed + demoed.

## Notes / decisions

- **Polish-heavy** — Tier 1 is the real sprint; Tier 2 + opt-in KWIs are stretch.
  Trim at review so it stays one sprint.
- The scrubber is the demo capstone: a Sol→Grayson run (11 days) compresses to
  seconds, ships sweep the map, the Manticore queue ticks `#3 → pops` — all live.
- Closes **Phase 2.5 Observer**; the Controller (file/route from the UI) opens the
  next arc.
