# 007 — First-class UI: vision & architecture

The Phase 2.5 front-end. This doc captures the **vision and conceptual model**
(agreed 2026-06-17). **Stack** and **sprint slicing** are deliberately left open
at the end — we settle those next, with the vision as the fixed point.

Companion to `004` (project plan), `006` (galaxy architecture). Supersedes the
one-paragraph Phase 2.5 sketch in `006` and the placeholder in `ui/README.md`.

## The one sentence

**Make the clock legible across the galaxy.** Everything the engine already
computes — a ship 6 days into hyper, a courier `queued #3` at the Manticore
Junction, planets at their *actual* current positions — visible at a glance and
explorable in depth. It is mission-control for a slow, real galaxy, **not a
game**: rich in detail and information, not flashy. How we present it is what
makes that distinction felt.

This started as "just watch ships move slowly and feel the payoff of time and
patience." That is still the prime motivator — but Sprints 012–019 revealed how
much richness the simulator can *show*, and the UI is where that richness lands.

## The shape: one app, two modes, shared furniture

**One application** (not two) — Observer and Controller both read the same data;
two apps would drift in look and feel. They are **two modes of one shell**,
switched via a main menu (hotkey to open; right-click held in reserve for a
future context menu).

Several pieces are **shared furniture** used by both modes:

- **The Big Map** — Observer's centerpiece; the Controller's Flight Planner also
  draws planned routes on it.
- **The Fleet Board** — fundamentally observational (the roster either mode
  reads), even though its write affordances are Controller-only.
- **The Side Data Panel**, **Ship Timeline**, **At-a-glance**, **Legend**,
  **Locate-a-ship** — reusable widgets (see the widget library below).

So **Observer ≈ Controller minus the write actions.** The Flight Planner is the
only Controller-exclusive surface. This is why Observer ships first: the
Controller's jobs are doable via the CLI tools in the meantime, and Controller is
then "Observer + one screen + buttons on panels already built."

## The Big Map — the spine (continuous level-of-detail zoom)

The defining, technically-hard feature: one continuous pan/zoom space with
**level-of-detail (LOD) transitions** that swap what is drawn as you descend.
**2D for now** (top-down: galaxy plane zoomed out, system ecliptic zoomed in).

| Zoom level | Renders | "At a glance" breadcrumb |
|---|---|---|
| Partial galaxy | systems as small circles, wormhole routes as thin lines | *(galaxy)* |
| System | star(s), planets, free-floating stations, hyper-limit ring, junction nexus | `Sol` + ship counts |
| Planet / region | moons, planet-tied stations | `Sol / Earth` |

- **The breadcrumb grows as you zoom** — the unifying thread that keeps "where am
  I" legible across a ~3-orders-of-magnitude scale jump. The At-a-glance box
  (top-left, from the MVP view) holds it; the legend sits bottom-right.
- **Regions/zones are LOD clustering, not a separate view.** When too many objects
  crowd a small area at a given zoom, collapse them into a region marker that
  expands on closer zoom. "Zoned Maps" = **the Big Map, centered on a system +
  zoom-constrained** (e.g. Sol clamps out to ~past Pluto / the inner Oort), toggled
  by hotkey. A zone's At-a-glance gains ship counts: total in system/zone, and for
  a system, ships *registered* to it split in-system / out-of-system.
- **Ships are a toggleable LOD layer, not always-on clutter.** Above system zoom,
  only *selected/tracked* ships render: a small dot with a leader line to its
  transponder code (leader ideally routes to miss other objects). Zoom in and the
  dot becomes a **heading vector** (or a fatter dot when at rest). Faction colors:
  start with assigned defaults, later user-remappable (a Haven-centric user paints
  the People's Navy blue; a Manticoran flips it).

### Smooth motion without a game loop

The engine is analytic and has no event push (and wants none). The UI **polls**
(`/fleet`, `/systems`, `/.../state`) every few seconds and **dead-reckons between
polls** — each `state` gives `(position, velocity, when)`, so the client
interpolates locally for smooth 60fps motion. The MVP Sol map already does this;
generalize it. No websockets in v1.

## The shared-widget library

The backbone of "this is a real app, not a few static pages":

- **Side Data Panel** — click any object (body / station / ship / junction) → its
  UniverseDB or ship-registry data; dismissable (right side, open to discussion).
  Includes a **reference-links button** surfacing the Fandom/source URLs we
  already store per fact.
- **Ship Timeline** — a reusable **1D flightplan widget**: a line of segments +
  symbols with a fill showing live progress. Used in the Side Data Panel for
  in-flight ships *and* in the Fleet Board. ASCII proof-of-concept (the UI renders
  it richer):

  ```text
                          sigma-draconis  manticore
                                |
   |-<-->-hl**************<>****V-+-W-----|
   |                                |   Sphinx
  earth                      beowulf-terminus

  "-"    n-space travel        "*"     hyperspace travel
  "hl"   hyper limit           "<-->"  turnover with coast
  "V"    translation out       "W"     wormhole junction
  ```

- **Locate-a-ship** — search + show/hide. **Explicitly designed to scale** from
  dozens → thousands (see scale below). Early: a dropdown of checkboxes + a search
  box ("find Nike fast"). Later: a richer control.
- **At-a-glance** / **Legend** — the MVP-view furniture, generalized; At-a-glance
  carries the breadcrumb + contextual counts.

## The Controller (mostly later)

- **Flight Planner** — pick an available ship → **prefill origin by state**
  (at-rest → current position; in-flight → "extend from current destination"; full
  rerouting deferred) → pick destination(s) + layovers → compute (the nav-planner)
  → submit to the sim. Later: **saved routes** (pick a ship, pick
  "Sphinx-Grayson-Courier-Run", go) and **non-traditional routes** (fly to a belt
  waypoint, then hyper into Trevor's Star from above the ecliptic).
- **Fleet Board** — the live roster (today's `just fleet` / shakedown, made live):
  every transponder, phase, location, ETA, `queued #N`. Shows the **Ship Timeline**
  inline for in-flight ships. **Filterable**, with filter controls that hide
  (collapse to an unobtrusive glyph) — click or hotkey to toggle. Click an entry →
  the Big Map flies to that ship at the right zoom.

### Realism note — minimum layover (filing policy)

Non-military ships need a **minimum layover** whenever they come to rest at a body
(clear arrival + departure) — proposed ~2 h. **UI-enforced for v1** is fine and
cheap. But it is really a **filing policy** that Phase-3 combat/admiral agents will
also need, so flag it as a **candidate to migrate into the engine later** — don't
let the UI become its permanent home.

## Cross-cutting truths the vision establishes

1. **A real application, not static pages.** Implies a real front-end stack and a
   served surface (its own small web server / container, or bundled — see Stack,
   open). Drops the earlier "minimal vanilla stack" hedge.
2. **Thousands in the sim, but few on the map at once.** The simulator should
   carry **thousands** of ships (bulk **tool-generated**; needs **more systems
   first**) — a near-term goal. But at most **~200 (typically a couple dozen) are
   *rendered* on the Big Map at any moment**, by selection/LOD. This splits the
   scale problem cleanly:
   - **Rendering is easy** — a few hundred dots/lines is comfortably within
     Canvas-2D's budget; WebGL is not needed for this.
   - **The roster *is* the scale challenge** — Locate-a-ship (search/filter over
     thousands), the data queries, and "which subset is tracked/visible" are where
     the engineering goes. *The ship-filter control deserves real design; the
     canvas does not need to be heroic.*
3. **2D now; 3D later as a separate artifact.** The main Big Map is 2D. A true 3D
   view is desired *eventually* but best realized as a **standalone rotatable /
   zoomable 3D model of the galaxy** (systems + wormhole links, **no ships**) — a
   "feel the shape of the galaxy" viewer, not a 3D version of the operational map.
   Keeps the operational UI tractable and the 3D piece scoped.
4. **Grafana dashboards stay a parallel track.** Rich ops dashboards remain wanted
   and are a **separate 1–2 sprint effort**, not replaced by this UI. Different
   audience: ops/metrics (Grafana) vs operator/explorer (this app).

## What the UI needs from the engine (API/contract gaps)

Naming these now so we don't retrofit:

- **Junction queue board endpoint** — already slated for **Sprint 020** (deployed
  `/fleet` queue display); the UI is its consumer. Likely `GET
  /junctions/{id}/queue` (who is queued, positions, ETAs).
- **Bulk galaxy-frame ship positions** — a map wants all tracked ships at once;
  the existing `/fleet` board may suffice.
- **Static topology in one shot** — systems + coords + wormhole edges for the
  galaxy graph (`/systems`, `/wormholes`, `/junctions` likely sufficient).
- **CORS vs same-origin** — depends on the serving model (Stack, open): a bundled
  front-end served by the engine needs no CORS (like today's Sol map); a separate
  service does.
- **Clock semantics** — prod runs rate 1.0 with `PUT /clock` 403'd, so a **timeline
  scrubber is a dev-only affordance**; prod is ambient real-time "now". The dev
  scrubber (fast-forward a multi-day trip into seconds) is a demo/dev superpower.

## Decisions — resolved (2026-06-17)

- **One app, two modes** (Observer / Controller) sharing the Big Map, Fleet Board,
  and widget library. Avoids look/feel drift.
- **2D Big Map now.** 3D deferred to a **separate rotatable galaxy-model viewer**
  (no ships), later.
- **Scale target: thousands of ships in the sim**, sooner rather than later (bulk
  tool-generated; needs more systems first) — but **only ~200 (usually dozens)
  rendered on the map at once**. So the scale work is the **roster / search /
  filter / queries**, not the renderer.
- **Observer first**, Controller second (CLI covers control meanwhile). Flight
  Planner is the only Controller-exclusive surface.
- **Poll + dead-reckon** for motion; no streaming in v1.
- **Min-layover** is UI-enforced for v1 but earmarked to migrate to the engine as a
  filing policy.
- **Grafana** is a parallel, separate track.

## Stack — decided (2026-06-17)

Chosen by letting the **Big Map rendering** lead the pick (it's the hard part).

> **SvelteKit (Svelte 5) + Canvas-2D for the Big Map (hybrid with a DOM overlay
> for chrome) + built to static assets, served by a small web server and
> bundle-able into the engine (same-origin, no CORS). PixiJS/WebGL held as an
> escape hatch for the map layer only; Tauri / Edge-appify deferred.**

- **Big Map renderer: Canvas 2D**, with a **DOM overlay** for labels, transponder
  leader-lines, and all panels ("fast for the many, ergonomic for the few"). A few
  hundred rendered objects is well within budget. Hit-testing via a simple spatial
  index (quadtree); **Konva** is an acceptable on-ramp if easier canvas events are
  wanted early. **PixiJS/WebGL** is the escape hatch *for the map layer only* —
  unlikely to be needed given ~200-objects-on-screen, kept as a principle so the
  swap stays localized.
- **Other renderers, per component:** **SVG** for the **Ship Timeline** widget
  (small, vector, interactive). Per-component renderer choices are fine.
- **Framework: SvelteKit (Svelte 5).** Lightest runtime around a 60fps imperative
  canvas loop; least ceremony for a dashboard-shaped app; stores fit poll/selection
  state; leaves the canvas alone; builds to static assets that drop into FastAPI
  like today's Sol map. (React is the fallback if max off-the-shelf components are
  wanted; the centerpiece is bespoke canvas either way, which mutes React's edge.)
- **Delivery: web-first.** Vite build → static assets; serve via a small web
  server or **bundle into the engine** for same-origin. **Appify in Edge** for a
  desktop feel at no cost. **Tauri** deferred (the app is a client to the remote
  engine; a native shell is a nicety, not a need). A JS web stack also keeps the
  future **3D galaxy-model viewer** cheap (Three.js as a separate route).
- **Why:** the Big Map is bespoke Canvas-2D code regardless of framework, so pick
  the framework that is lightest *around* that loop and cheapest to ship — Svelte
  to static assets the engine can serve. Canvas-2D meets "a few hundred dots at
  60fps, rich-not-flashy" without WebGL's complexity or SVG's DOM ceiling, and
  isolating the renderer keeps the (improbable) Pixi upgrade a localized swap.

## Slicing — decided (2026-06-17)

Sequential numbers, no gaps; **deploy to kubsdb every sprint** (the demo is ours).
Observer-first; the engine queue endpoint goes first (it's the Grafana data
surface and unblocks the UI queue view later).

| # | Sprint | Track |
|---|---|---|
| **020** ✅ | **engine: junction queue endpoint** — implemented the contracted `GET /junctions/{id}/queue` (`JunctionQueue`); deployed `/fleet` board resolves the whole fleet together (real-ship interleaving) + surfaces `queue_position`; per-junction queue depth/wait metrics for Grafana; `just queue-board`. | engine |
| 021 ✅ | UI foundation + galaxy graph — scaffolded `ui/` (SvelteKit 5 + Canvas-2D), build wired into `just`, served same-origin at `/ui` (multi-stage image). Galaxy graph (`/systems`+`/wormholes`+`/junctions`), pan/zoom, click → Side Data Panel, At-a-glance + legend. | ui |
| 022 ✅ | LOD spine: zoom into systems — galaxy↔system scenes (double-click / `Enter` / zoom-in to enter, `Esc`/zoom-out to leave); heliocentric top-down (star, planets/moons live, hyper-limit ring, ride-on stations); breadcrumb; zone mode (`z`), fit (`f`); reserved `keymap`. Engine: `GET /systems/{id}` (+hyper limit/stars/binary), `/systems/{id}/places`, Sol-bodies delegate. | ui |
| 023 ✅ | Live ships + Fleet Board — sim-clock + dead-reckoning render loop; ships on both scenes (galactic motes + in-system dots/heading-vectors); Fleet Board rail (collapsible, search, click-to-fly) with the Ship Timeline; Locate-a-ship (search + per-ship show/hide). Engine: `GET /fleet/{tp}/route`. | ui |
| 024 ✅ | Junction queue panels — a nexus marker in the host system opens a live queue panel (consumes 020): ordered real + phantom entries with a per-second `transit in MM:SS` countdown off the shared sim clock; `Esc` backs out progressively. | ui |
| 025 ✅ | Polish + dev time controls — dev-gated **time scrubber** (play/pause via rate 0, rate presets, step, jump; `Space`/`,`/`.`), **faction colours**, **layer toggles** (`l`), **help overlay** (`?`), itinerary line + leader-line de-collision. Engine: `ClockUpdate.rate` `ge=0`. **Observer complete.** | ui |
| **026** ✅ | **engine: `POST /plan`** — relocated the finder into `hvsim.route.find` (`plan_route` + `plan_route_multi`); `tools/nav-planner` is now a thin CLI wrapper. `POST /plan` → `{filed, route}` (multi-destination, per-waypoint layovers; resolved preview); 404/422/503. Min-layover left to the UI. | engine |
| 027 ✅ | UI Flight Planner — `m` opens the planner: pick ship (from `GET /fleet/ships` catalog) → origin + ordered destinations + layovers (non-military default ≥2 h) → `POST /plan` → preview (galaxy path highlight + ETA + Ship Timeline) → submit (`POST /fleet/routes`) → joins the live board. Engine: `Universe.ships()` + `GET /fleet/ships`. | ui+engine |
| 028 | Controller extras (later) — saved routes ("Sphinx-Grayson-Courier-Run"), non-traditional waypoint routes (belt waypoint → hyper from above the ecliptic), re-route a moving ship. | ui+engine |
| deferred | Grafana dashboards — separate 1-2 sprint effort; revisit at each new data surface (next: the 020 queue metrics). | ops |

Build order parallels the engine's own: topology -> motion -> operate -> observe.
Stop and refine between sprints as needed.

## Controller — planned (2026-06-18)

The Observer is done; the Controller lets a user **file/route ships from the UI**.
Arc: **026** (engine `/plan`) → **027** (Flight Planner UI) → **028** (extras,
later). The Controller is "Observer + write actions" — it reuses the map, board,
panels, and the existing `POST /fleet/routes` / `DELETE /fleet/{tp}/route`.

### The crux: where route-finding lives (settle for 026)

Today the route-finder is **`tools/nav-planner`, which depends on `hvsim`**. The
UI can't run Python, so it needs an HTTP **`POST /plan`**. But the engine API is
`hvsim.api` — if it imported `nav_planner`, that's `hvsim → nav-planner → hvsim`,
**circular**. So:

- **Recommended:** **relocate the finder into the engine** — move the Dijkstra
  search (`_search`/`plan_route`, ~120 lines, pure graph over `Universe`, no extra
  deps) into `hvsim` (e.g. `hvsim.route` gains `find_route`, or a new `hvsim.nav`);
  `tools/nav-planner` becomes a thin CLI wrapper that imports it. The API then
  serves `/plan` from `hvsim`. This **revises** the earlier "route-finding stays in
  the tool" principle — acknowledged: HTTP planning makes finding a first-class
  engine capability. Physics + finding both live in `hvsim`; the *UI* still owns no
  logic.
- Rejected: API depends on the `nav-planner` package (awkward circular/packaging);
  a separate planner microservice (overkill).

### `POST /plan` shape (026)
- Input: `{ ship (transponder), origin {system, body}, waypoints: [{system, body,
  layover_s?}] }` — an **ordered list of must-visit destinations** (multi-planet),
  each with an optional layover. Output: the **filed-route JSON** (`to_filed` shape)
  **plus** a compiled preview (segments + ETA) — *computed, not filed*. The UI
  previews it, then submits the filed-route to `POST /fleet/routes` to commit.
- **Multi-destination is core, not deferred.** The engine `Route` is already a list
  of legs with per-leg layovers (the `Sol→Beowulf→Manticore→Grayson` demo flies
  one); `/plan` runs the finder for each consecutive `(from, to)` hop and
  concatenates the legs (inserting layovers at each waypoint). Single-destination is
  just a one-waypoint list. Reuses the relocated finder + `compile_route`; 404
  unknown ship/system, 422 unroutable.

### Min-layover filing policy — UI-enforced (decided 2026-06-18)
- Non-military ships get a default layover (~2 h) to clear arrival+departure,
  **enforced in the UI** (027) — a value we expect to **vary later**. `/plan` does
  not enforce it. It is really a **filing policy** Phase-3 admirals will need too,
  so it stays earmarked to migrate into the engine when that variation arrives.

### Flight Planner UI (027)
- A Controller **mode** (the reserved `m` menu switches Observer↔Controller). Pick
  an available ship → **prefill origin by state** (at-rest → current; in-flight →
  "extend from destination", re-route deferred to 028) → pick destination(s) +
  layovers → `POST /plan` → preview the route on the map + a summary → **submit**.
  Abort/clear via `DELETE`. Re-uses the Ship Timeline for the preview.

## Open — to settle next (NOT decided here)

- **Re-routing a moving ship** — deferred to 028 (the at-origin guard rejects it
  today); pairs with "extend from destination" for in-flight ships.

_Resolved 2026-06-18: route-finder **relocates into `hvsim`** (026); min-layover is
**UI-enforced** (027); multi-destination routing is **in scope for 026/027**._
