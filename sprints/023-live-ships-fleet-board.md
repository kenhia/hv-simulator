# Sprint 023 — Live ships + the Fleet Board

The payoff sprint: **watch ships crawl across the galaxy and through systems in
real time.** Ships appear on both scenes (galaxy motes in hyper, in-system dots),
move smoothly via dead-reckoning between polls, and a **Fleet Board** rail lists
the fleet with a **Ship Timeline** for those under way. This is the prime
motivator — time + patience made visible — realized on the 021/022 map.

Vision: [`planning/007`](../planning/007-ui-vision.md). Builds on 022's scenes +
camera + chrome.

## Goal

Ships on the map, live: a hyper-bound ship slides along its interstellar line in
the galaxy view; an in-system ship drifts on its heliocentric top-down — both
dead-reckoned at 60fps between ~5s state polls, driven by the sim clock. The
Fleet Board (collapsible, filterable) lists every tracked ship (phase, location,
ETA, `queued #N`); click one to fly to it; in-flight ships show the Ship Timeline.

## The data (mostly already served)

- `GET /fleet` — the board roster (transponder, ship, phase, system, eta,
  percent, `queue_position`).
- `GET /fleet/{transponder}/state` — **position (`km`, frame coords), velocity
  vector (`km_s`), `when`, `frame`, `system`, `phase`, `eta`** — everything
  dead-reckoning needs (`pos(t) = pos.km + km_s·(t − when)`).
- `GET /clock` — `sim_epoch`, `real_epoch`, `rate` → the UI computes **simNow()**
  locally (`sim_epoch + (wallNow − real_epoch)·rate`) for smooth motion, resyncing
  periodically. (Prod = rate 1.0; dev may jump/accelerate.)
- **New: `GET /fleet/{transponder}/route`** → the compiled `RouteOut` (segment
  kinds + boundaries) the **Ship Timeline** needs. (The POST already returns this
  shape; expose a GET. Recompiled-on-query like the rest.)

## Design

### Sim clock + dead-reckoning (the live heartbeat)
- `clock.ts` (pure-ish): hold `{sim_epoch, real_epoch, rate}` from `/clock`;
  `simNow()` extrapolates locally; resync every ~30s. Unit-test the extrapolation.
- `deadReckon(pos_km, vel_km_s, when, now)` (pure): linear extrapolation, unit-
  tested. Each tracked ship caches its last `state`; a `requestAnimationFrame`
  loop recomputes positions + redraws so motion is smooth, not 5-second steps.

### Ships on the scenes (an LOD layer)
- **Galaxy scene** — a ship with `frame == "galactic"` (in hyper) is a **mote** at
  its galactic position (`km → ly`, projected X–Z like systems) + a leader line to
  its transponder. A heliocentric/in-system ship rides at its system's node. Above
  system zoom only **tracked** ships draw (not the whole fleet) — see Locate-a-ship.
- **System scene** — a ship whose `system` is the current one and `frame ==
  "heliocentric"` draws at its `position.au`; a small **heading vector** when
  moving, a fatter dot at rest.
- Click a ship → the Side Data Panel (a `shipRows` detail: phase, ETA, speed,
  `queued #N`) + its Ship Timeline.

### The Fleet Board (the operational rail)
- A side rail listing tracked ships: transponder, name, phase, location, ETA,
  `queued #N`. Polls `/fleet`. Click an entry → select + **fly the map to it** (and
  enter its system if it's in-system). **Filter controls that hide** (collapse to a
  glyph; click / hotkey to toggle) — phase/nation filters; a search box.
- In-flight rows embed the **Ship Timeline**.

### Ship Timeline widget (reusable)
- A 1D flightplan strip from `/fleet/{tp}/route`'s segments: `-` n-space, `hl`
  hyper-limit, `*` hyper, `<-->` turnover, `V` translation, `W`/queue, with a
  **progress fill** at the ship's current point (from `percent_complete` / segment
  + simNow). Used in the board and the data panel.

### Locate-a-ship (built to scale)
- Search box + a list with show/hide toggles driving the **tracked set** (which
  ships render above system zoom). v1: default-track the (small) active fleet;
  search filters; designed so dozens → thousands stays usable (the renderer only
  ever draws the tracked subset, ≤ a couple hundred — see 007).

## Scope

1. Engine: `GET /fleet/{transponder}/route` → `RouteOut` (404 if no active route).
2. `clock.ts` + `deadReckon` (pure + Vitest); a sim-clock store.
3. Fleet polling store (`/fleet` + per-tracked `/.../state`); a rAF redraw loop.
4. Ships on GalaxyMap (galactic motes + leaders, tracked-only) and SystemMap
   (in-system dots + heading vectors), dead-reckoned.
5. Fleet Board rail (collapsible, filter + search, click-to-fly); `shipRows`.
6. Ship Timeline widget (from the route segments) in board + panel.
7. Locate-a-ship (search + show/hide → tracked set).
8. Tests: Vitest (clock extrapolation, deadReckon, timeline segment mapping);
   engine test for the route endpoint.

## Out of scope (later)

- **Junction queue panels** (the `#3 → pops` board at a nexus) — 024 (consumes
  020's endpoint).
- **Faction colours, main menu, dev time scrubber, leader-line de-collision,
  region clustering** — 025 / later.
- **Binary star geometry** (KWI #69), **label click-targets** (#70), **scale bar**
  (#71) — filed, independent.
- **Filing / re-routing from the UI** (Controller) — later.

## Tasks

- [ ] Engine `GET /fleet/{transponder}/route` (+ test).
- [ ] `clock.ts` (simNow extrapolation) + `deadReckon` helper, both unit-tested.
- [ ] Polling stores (fleet roster + per-ship state) + a rAF redraw loop.
- [ ] Galaxy ships (galactic motes, km→ly, leaders, tracked-only).
- [ ] System ships (heliocentric dots + heading vectors).
- [ ] Fleet Board rail (collapsible/filter/search, click-to-fly) + `shipRows` panel.
- [ ] Ship Timeline widget (route segments + progress) in board + panel.
- [ ] Locate-a-ship (search + toggles → tracked set).
- [ ] Vitest + engine test; `just check` + `just contracts` green; deploy + demo.

## Acceptance criteria

- With a fleet filed (e.g. `just shakedown` / the live couriers), ships appear and
  **move smoothly** on both scenes — a hyper ship sliding along its line, an
  in-system ship drifting — without 5-second jumps.
- The Fleet Board lists tracked ships with phase / location / ETA / `queued #N`;
  clicking one flies to it; in-flight rows show the Ship Timeline.
- Locate-a-ship filters/searches; only tracked ships draw above system zoom.
- `GET /fleet/{tp}/route` returns the route segments; `just check` (engine + UI) +
  `just contracts` green; deployed + demoed on kubsdb.

## Notes / decisions

- **Largest UI sprint so far** (live loop + board + timeline + locate). If it runs
  long we can split (e.g. 023a: clock + dead-reckon + ships on both scenes; 023b:
  Board + Timeline + Locate-a-ship) — decide at build time.
- **Dead-reckoning is linear** (constant velocity between polls); good enough at
  these cadences. Polls correct any drift. Accel phases (brachistochrone) will
  show tiny seams at boundaries — acceptable v1.
- The rAF loop is the first **continuous render** in the UI (021/022 redraw on
  change). Keep it behind the scene modules; pause it when the tab is hidden.
- simNow lets prod run truly live (rate 1.0) and dev fast-forward (jump/rate) drive
  the same view — the dev time scrubber (025) becomes a control on this clock.
