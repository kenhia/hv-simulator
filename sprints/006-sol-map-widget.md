# Sprint 006 — Sol-map dashboard widget (Phase 1 / M5)

Completes milestone **M5** from `planning/004-project-plan.md` — the last open
Phase 1 item. Closes out Phase 1 before the Phase 1.5 operational work.

## Goal

A simplest-possible 2D top-down map of the Sol system, served by the existing
API, that polls `/bodies` and `/ships` and shows where everything is right now —
proving the API shape is right and giving a first way to *watch* ships move.

## Scope

- A **single self-contained `index.html`** (HTML + CSS + vanilla JS, Canvas 2D) —
  no build step, no Node toolchain, no new runtime dependencies.
- Served by the existing FastAPI app at **`GET /`** (same origin → no CORS).
- Renders a top-down ecliptic view: Sun centered, bodies (planets/moons/stations)
  as dots colored by kind, ships as distinct markers with a label
  (name, phase, speed as fraction of c, percent-complete).
- **Client-side dead-reckoning**: between polls, advance each ship locally every
  animation frame using the velocity vector `/state` already returns
  (`pos += vel·dt`), and snap to the authoritative position on each poll. Motion
  is smooth regardless of poll cadence.
- **Poll cadence** (see math below): `/ships` + `/clock` every **15 s**,
  `/bodies` every **~5 min**, **30 s** hard max for `/ships`. Redraw runs at
  animation-frame rate off the dead-reckoned state, not the poll.

## Decisions (baked in; flag if you disagree)

- **Vanilla static page served by the API.** Matches "simplest possible /
  not flashy," keeps it one container and one origin.
- **2D top-down, plot (x, y) in AU, ignore z.** z is tiny for planets and ships;
  a top-down plot is the honest "tactical plot" view.
- **Default radial extent ≈ 11 AU** (Mercury → Saturn + Titan Station — the v1
  action zone). Uranus/Neptune fall off-view in v1; a zoom/extent control is a
  noted later nicety, not this sprint.
- **Polling (not push), with cadence sized to the display.** `/ships` every 15 s,
  `/bodies` every ~5 min, 30 s max — derived below. Dead-reckoning decouples
  visual smoothness from the poll rate.

## Out of scope

- 3D, pan/zoom, orbit trails/prediction, hover tooltips beyond a basic label.
- WebSocket/SSE live push (polling only).
- Mobile/responsive polish; theming.
- A JS test toolchain — the page is verified by a backend route test plus visual
  inspection, not JS unit tests.
- Auth (the API stays open on the LAN, as today).

## Tasks

- [x] `static/index.html`: fetch `/ships` + `/clock` every 15 s and `/bodies`
      every ~5 min; project to a top-down AU plot, draw Sun/bodies/ships, label
      ships, show a legend and the sim clock.
- [x] Dead-reckoning: on each `requestAnimationFrame`, advance each ship by
      `velocity · (now - last_poll)` from its last polled position; snap to the
      authoritative position on the next poll. Bodies are treated as static
      between their (rare) refreshes.
- [x] Serve it at `GET /` from the FastAPI app (FileResponse/HTMLResponse; no new
      deps). Keep `/docs` for the API.
- [x] Backend test: `GET /` returns 200 HTML that references the consumed
      endpoints.
- [x] README: note the map is at `http://<host>:4667/` (API docs at `/docs`).
- [x] Manual visual check: seed a ship on a short trip (optionally jump a dev
      clock) and confirm the marker advances between polls; record the result.

## Acceptance criteria

- `GET /` serves a self-contained HTML map page (200), with **no new runtime
  dependencies** added.
- The page renders the Sun, all in-view bodies, and any ships from live
  `/bodies` + `/ships`; `/ships` refreshes every 15 s (≤ 30 s), `/bodies` ~5 min.
- Ship markers show name + phase + speed (fraction c) + percent-complete. Motion
  is **smooth** (dead-reckoned each frame), not steppy; a new ship appears within
  one `/ships` poll (≤ 15 s). Verified by seeding a short trip and/or jumping a
  dev clock.
- The page consumes the `/bodies` and `/ships` response shapes as-is — i.e. it
  exercises and validates the API contract (M5's purpose).
- Validation gate green: `uv run pytest` (incl. the route test), `ruff check`,
  `ruff format --check`.

## Notes / decisions

- **Poll-cadence math.** Light crosses 1 AU in 499 s. At 4K a square top-down map
  spanning ±11 AU is ~98 px/AU (1 px ≈ 1.52e9 m). A ship crossing one pixel takes
  ~5 s at 1.0c, ~8.5 s at our 0.6c cap, but **~25 s at the realistic in-Sol peak
  of ~0.2c** (Earth→Saturn tops out at 0.199c). Half-that (Nyquist) is ~13 s →
  rounded to a **15 s** `/ships` poll. Planets move ~1 px/hour at this scale, so
  `/bodies` refreshes every ~5 min. Dead-reckoning keeps motion smooth between
  polls, so the 15 s figure is about freshness (new ships, plan changes), not
  animation. 1.0c was considered and rejected — no ship reaches it.
- This sprint also carries the **Phase 1.5 plan edit** to `planning/004` (added
  last session, currently uncommitted) onto its branch — it lands with this PR.
- Inner planets cluster near the Sun at an 11 AU extent; acceptable for v1. If it
  bugs us, a log-radial option or an inner/outer toggle is an easy follow-up.
- Static assets live in `static/` at the repo root (or `src/hvsim/api/static/`);
  decide at build time — a single inlined file needs no mount.

## Outcome — DONE

- Shipped on branch `sprint-006-sol-map-widget`. 61 tests pass; ruff + format
  clean. **Phase 1 is now fully complete (M1-M5).**
- `src/hvsim/api/static/index.html` — one self-contained page (Canvas 2D, vanilla
  JS, no build step, no new deps), served at `GET /` via `FileResponse`.
- Dead-reckoning implemented: ships advance each animation frame from the last
  polled position using the `/state` velocity vector (converted km/s -> AU/sim-s),
  honouring `clock.rate` (frozen when rate 0); snap to truth on each poll.
- Cadence: `/ships` + `/clock` every 15 s, `/bodies` every ~5 min (planets are
  ~static at 4K's ~98 px/AU). Renders Sun, orbit rings, bodies by kind, ship
  markers + labels (phase, speed in c, %); HUD shows sim clock/rate and counts.
- Chose `src/hvsim/api/static/` so the file ships in the wheel; **verified the
  built Docker image serves the map** (HTTP 200, text/html). Confirmed a
  mid-transit ship exposes a non-zero velocity vector (0.199c) for dead-reckoning.
- Decision recap: served at `/`, Canvas (not SVG), 11 AU extent. Inner planets
  cluster (acceptable v1); zoom/log-radial is a noted follow-up.
