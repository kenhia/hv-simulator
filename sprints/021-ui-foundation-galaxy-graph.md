# Sprint 021 — UI foundation + galaxy graph

The first Phase 2.5 sprint and the **stack proof**: stand up the `ui/` front-end
end-to-end — scaffold → build → serve → **deploy to kubsdb** — on the easiest real
data (the static galaxy graph), so the whole toolchain is de-risked before we climb
the hard LOD-zoom spine (022) or add live ships (023). Vision + stack are fixed in
[`planning/007`](../planning/007-ui-vision.md); this sprint settles the serving-model
specifics it left open.

## Goal

A deployed web app that draws the **galaxy graph**: placed systems as nodes in the
galactic frame, wormhole links as edges, pan + zoom, click a system → a Side Data
Panel. At-a-glance (top-left) + legend (bottom-right) furniture. Served by the
engine (same-origin) and reachable on kubsdb. No live ships, no system zoom yet.

## Stack (from 007 — fixed)

- **SvelteKit (Svelte 5)** + **TypeScript** + **Vite**, `adapter-static` (a
  client-only SPA — no SSR), built to static assets.
- **Canvas-2D** for the map (one `<canvas>` + a DOM overlay for chrome/panels);
  the renderer is isolated behind a module so a Pixi/WebGL swap stays localized
  (it won't be needed at this scale).

## Design

### Data (all already served by the engine)
- `GET /systems` → nodes. Plot only **placed** systems (`coordinates != null`);
  stubbed systems (Sol, Gregor, …) have null coords and are skipped (note the count
  in At-a-glance so the omission is visible, not silent).
- `GET /wormholes` → edges (`from_system_id` / `to_system_id`); draw an edge only
  when **both** endpoints are placed.
- `GET /junctions` → mark junction host systems (a ring/badge), foreshadowing the
  queue board (024). Read-only here.

### Rendering
- **2D top-down projection** of the galactic frame: plot `(x_ly, y_ly)`, ignore
  `z` for now (z is the later 3D-model viewer's job, 007). A **camera** (scale +
  pan offset) maps galactic ly ↔ screen px; mouse-drag pans, wheel zooms about the
  cursor. The projection/camera math is a **pure module** (unit-tested).
- Nodes: small circles (binary systems flagged); wormhole edges as thin lines.
  Rich-not-flashy. Hit-testing via nearest-node search (no spatial index needed at
  ~dozens of systems).

### Chrome (DOM overlay, the reusable widgets begin here)
- **At-a-glance** (top-left): galaxy-level counts (placed / stubbed systems,
  wormhole links). The breadcrumb that grows on zoom is 022.
- **Legend** (bottom-right): node / binary / junction / wormhole keys.
- **Side Data Panel** (right, dismissable): click a system → its `/systems` data
  (name, nation, binary, distance_ly, coordinates). The reference-links button and
  richer data are later.

### Serving & build (settles 007's open "serving model")
- **Bundled into the engine**, same-origin (no CORS): the engine mounts the built
  SPA via `StaticFiles` at **`/ui`** (with an SPA HTML fallback). The legacy Sol
  map stays at `/` until the SPA subsumes it (022/023); `/docs` unchanged.
- **`just ui-dev`** — Vite dev server, proxying API calls to the engine
  (`HVSIM_HOST`/`PORT`). **`just ui-build`** — `vite build` → `ui/dist`.
- **`just ui-check`** — `svelte-check` (types) + lint/format + Vitest unit tests;
  folded into **`just check`** so the gate covers the UI. Node toolchain: **npm**.
- **Deploy** — multi-stage Dockerfile (a Node builder stage emits `ui/dist`,
  copied into the Python runtime image) so `just deploy` stays one command and the
  image is self-contained. Deployed to kubsdb and demoed.

## Scope

1. Scaffold `ui/` (SvelteKit + TS + Vite, adapter-static); `ui/README.md` updated
   to point at the real app + `planning/007`.
2. API client (typed) for `/systems`, `/wormholes`, `/junctions`.
3. Canvas-2D galaxy graph: nodes + edges, camera (pan/zoom), node hit-testing.
4. Chrome: At-a-glance, legend, Side Data Panel (click a system).
5. Engine serves the SPA at `/ui` (StaticFiles + SPA fallback); legacy `/` intact.
6. `just ui-dev` / `ui-build` / `ui-check`; `ui-check` folded into `just check`.
7. Multi-stage Dockerfile builds + bundles the SPA; deploy to kubsdb.
8. Tests: Vitest unit for the projection/camera math; `svelte-check` clean.

## Out of scope (later sprints)

- **System top-down + continuous zoom + breadcrumb + zones** — 022.
- **Live ships, Fleet Board, dead-reckoning, Ship Timeline, Locate-a-ship** — 023.
- **Junction queue panels** (consume 020's endpoint) — 024.
- **Main menu / Observer↔Controller modes, dev time controls, faction colors,
  detail views** — 025.
- **3D galaxy-model viewer** — later (007).
- **Flight Planner / any write actions** — Controller, later.

## Tasks

- [ ] Scaffold `ui/` (SvelteKit 5 + TS + Vite, adapter-static); update `ui/README.md`.
- [ ] Typed API client + a small fetch/poll store (poll cadence trivial here).
- [ ] Canvas-2D renderer: galaxy nodes + wormhole edges; pure camera/projection
      module (galactic ly ↔ screen px).
- [ ] Pan (drag) + zoom (wheel-about-cursor); nearest-node hit-testing.
- [ ] At-a-glance, legend, Side Data Panel (system click).
- [ ] Engine `StaticFiles` mount at `/ui` + SPA fallback; legacy `/` unchanged.
- [ ] `just ui-dev` / `ui-build` / `ui-check`; fold `ui-check` into `just check`.
- [ ] Multi-stage Dockerfile (Node build → Python runtime); `just deploy` bundles it.
- [ ] Vitest unit (projection/camera); `svelte-check` clean; `just check` green.
- [ ] Deploy to kubsdb + demo; CLAUDE.md + `planning/007` (mark 021 landed) updated.

## Acceptance criteria

- `just ui-dev` runs the app locally against the engine; `just ui-build` emits a
  static bundle.
- The deployed engine serves the galaxy-graph app at `/ui` on kubsdb: it renders
  every **placed** system + the wormhole edges between placed systems, pans and
  zooms smoothly, and a system click opens a Side Data Panel with its data.
- At-a-glance shows placed/stubbed/link counts; legend present; the stubbed-system
  omission is visible (not silent).
- `just check` (now incl. `ui-check`: svelte-check + lint + Vitest) and
  `just contracts` are green.

## Notes / decisions

- **Thin vertical slice on purpose.** The win is proving scaffold → build → serve →
  deploy on simple static data; richness comes in 022–025. Resist pulling system
  zoom or live ships forward.
- **Serving settled:** bundled into the engine, `/ui`, same-origin. Revisit a
  sibling container only if the front-end build starts to dominate the image.
- **Renderer isolation** is the load-bearing choice: keep all Canvas drawing behind
  a module boundary so 022's LOD spine and a possible future WebGL swap don't ripple.
- The legacy Sol map at `/` is the POC the system view (022) generalizes into the
  SPA; it retires when the SPA covers system zoom.
