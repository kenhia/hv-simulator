# Terminology

A quick-reference glossary for the acronyms and jargon scattered across the specs,
planning docs, and code. Alphabetical; each entry is **tagged** so you can tell
which world it belongs to. A term can carry more than one tag.

**Tags:** `[sci]` real-world science/physics · `[lore]` Honorverse (David Weber)
canon · `[sim]` the engine / simulation architecture · `[ui]` the Phase 2.5
front-end · `[ops]` tooling / deploy / observability · `[proj]` project-specific
convention.

---

- **0.6c / 0.5c** `[lore][sci]` — real cruise velocities in hyper: warships ~0.6c,
  merchants ~0.5c. The apparent speed is this × the band's velocity multiplier.
- **apastron / periastron** `[sci]` — the farthest / closest points of an orbit
  (here, of a binary pair's mutual orbit). Manticore-A↔B: 827 / 650 light-minutes.
- **artifact (universe artifact)** `[sim][proj]` — the compiled read-only SQLite
  (`build/universe.db`) the engine loads: systems, bodies, wormholes, ships,
  hyperspace model. Built from `data/` JSON by the universe-compiler.
- **AU (astronomical unit)** `[sci]` — Earth–Sun distance, ~1.496e11 m. In-system
  positions are reported in AU. 1 AU ≈ 8.317 light-minutes.
- **barycenter** `[sci]` — the common center of mass two stars orbit. A binary's
  planets orbit a star that is itself offset from the barycenter (the system origin).
- **band (hyper band)** — see *hyperspace band*.
- **brachistochrone** `[sci][sim]` — a constant-thrust "accelerate, flip at the
  midpoint, decelerate" trajectory. The default in-system flight profile.
- **c** `[sci]` — the speed of light. Velocities are often given as a fraction
  (`0.6c`); the n-space cap is 0.6c.
- **canon / `canon:false`** `[proj][lore]` — whether a datum comes from Weber's
  books/wiki (`canon:true`) or is fabricated by us (`canon:false`, e.g. invented
  orbits and galactic coordinates).
- **Canvas 2D** `[ui]` — the browser immediate-mode raster API the maps render with
  (chosen over SVG/WebGL for thousands-of-dots performance at low complexity).
- **CC BY-SA** `[proj]` — Creative Commons Attribution-ShareAlike, the license on
  `data/` (separate from the MIT code).
- **contract (boundary contract)** `[sim][proj]` — the versioned, language-agnostic
  seam in `contracts/`: the artifact SQL **DDL** + the engine **OpenAPI**. Frozen
  per minor version so tools / engine / UI stay decoupled.
- **CORS** `[ui]` — Cross-Origin Resource Sharing. Avoided here by serving the SPA
  same-origin (the engine hosts it at `/ui`).
- **CSR / SSR / SPA** `[ui]` — Client-Side Rendering / Server-Side Rendering /
  Single-Page App. The UI is a client-only SPA (no SSR).
- **dead-reckoning** `[ui][sim]` — extrapolating a ship's position between API polls
  from its last `(position, velocity, time)` so motion looks smooth at 60fps.
- **DDL** `[sim]` — Data Definition Language: the `CREATE TABLE …` SQL defining the
  artifact's shape (`contracts/universe-artifact/schema.sql`).
- **DES (discrete-event simulation)** `[sim]` — the engine's core (Sprint 013):
  filed segments become boundary *events*; `state(T)` replays events then evaluates
  the active segment analytically. No per-tick game loop; zero drift.
- **Dijkstra** `[sim]` — the shortest-path algorithm the `nav-planner` uses over the
  system/wormhole graph to pick a route.
- **ephemeris** `[sci][sim]` — a model of where bodies are over time. Sol uses real
  JPL Keplerian elements; other systems use fabricated orbits.
- **ETA** `[proj]` — estimated time of arrival (overall, or to the next boundary).
- **FCFS** `[sim]` — First-Come-First-Served: how ships serialize through a wormhole
  junction's transit queue (Sprint 019/020).
- **FK (foreign key)** `[sim]` — a relational reference between artifact tables.
- **frame (heliocentric / galactic)** `[sci][sim]` — which coordinate origin a
  position is in: a system's star (heliocentric) or the Sol-origin galaxy frame
  (galactic, used for interstellar hyper legs). `ShipState.frame` says which.
- **g (gee)** `[sci]` — standard gravity, 9.80665 m/s²; ship accelerations are given
  in g (e.g. a 250 g impeller).
- **galactic north / south / east / west** `[sci][lore]` — coarse compass bearings
  canon gives for inter-system directions. Our frame: +Z north, +X east, Y reserved
  (the disk is the X–Z plane; "north" is in-plane, not "up").
- **galactic plane / midplane / thin disk** `[sci]` — the disk the galaxy's stars
  lie in. Settled systems sit within ~±300 ly of the midplane (see KWI #68).
- **heliocentric** `[sci]` — centered on a system's star. See *frame*.
- **HMS / GNS / SLNS / RHNS …** `[lore]` — ship-name prefixes by navy (Her Majesty's
  Ship / Grayson Navy Ship / Solarian League Navy Ship / Republic of Haven …).
- **hull classification** `[lore]` — warship size codes: DN dreadnought, SD
  superdreadnought, BC battlecruiser, CA heavy cruiser, CL light cruiser, DD
  destroyer, etc.
- **hyper / hyperspace** `[lore][sci]` — the higher-dimensional space ships cross
  for fast interstellar travel, layered in **bands**.
- **hyper limit** `[lore][sci]` — the distance from a star inside which you can't
  safely translate into/out of hyper (gravity too strong). Ships run out to it on
  impeller drive before going hyper. Per-star, in light-minutes.
- **hyperspace band** `[lore][sci]` — a layer of hyperspace (Alpha, Beta, … Iota);
  higher bands give a larger **velocity multiplier** (apparent = multiplier × real
  velocity), per Weber's canon chart. Each ship class has a max band.
- **impeller (wedge)** `[lore]` — the reactionless drive producing a ship's normal-
  space acceleration (the gravity "wedge").
- **J2000** `[sci]` — the standard astronomical epoch (2000-01-01 12:00 TT) the JPL
  orbital elements are referenced to.
- **JPL** `[sci]` — NASA's Jet Propulsion Laboratory; source of the approximate
  Keplerian elements used for Sol's real planet positions.
- **`just` / justfile** `[ops]` — the task runner orchestrating the workspace
  (`just check`, `just build`, `just deploy`, `just ui-dev`, …).
- **Keplerian elements** `[sci]` — the six orbital parameters (semi-major axis,
  eccentricity, inclination, …) that define an orbit analytically.
- **kubsdb** `[ops][proj]` — the homelab host the service deploys to
  (`kubsdb:4667`); also runs Prometheus/Grafana.
- **KWI** `[proj]` — "Ken's Work Items," the backlog tracker (project `hv-simulator`,
  referenced as `KWI #NN`).
- **layover** `[sim]` — a segment kind: holding station at a body for a fixed dwell.
- **light-minute / light-second** `[sci]` — distance light travels in that time
  (1 lmin ≈ 1.799e10 m). Hyper limits and binary separations are in light-minutes.
- **LOD (level of detail)** `[ui]` — swapping what's drawn by zoom: galaxy nodes →
  system top-down → bodies; and ships only rendering above a zoom when tracked.
- **ly (light-year)** `[sci]` — ~9.461e15 m; inter-system distances and the galactic
  frame are in ly.
- **`nation.class.hull`** `[proj]` — the dotted **transponder** format (stable
  integer codes), e.g. `347.5.3` = Star Kingdom of Manticore · Nike class · hull 3.
- **nav-planner** `[sim][proj]` — `tools/nav-planner`, the route-finder (Dijkstra)
  that emits a filed-route JSON the engine flies.
- **nexus** `[lore]` — the central node of a wormhole junction; all traffic passes
  through it regardless of destination terminus.
- **n-space (normal space)** `[lore][sim]` — ordinary space (vs hyperspace); impeller
  travel happens here.
- **OpenAPI** `[sim]` — the machine-readable HTTP API spec
  (`contracts/engine-openapi.yaml`), the other half of the boundary contract.
- **OpenEndedSegment** `[sim]` — a segment with no fixed end time, resolved at
  arrival by a stateful resolver (the seam the wormhole queue uses).
- **PD (Post Diaspora)** `[lore]` — the Honorverse calendar. `SimClock` carries a
  PD ↔ T-year ↔ epoch mapping (timeline anchored ~1890 PD); it labels the clock
  without changing real time.
- **phantom traffic / `traffic_intensity`** `[sim][proj]` — fabricated background
  ships that give a junction queue depth. `traffic_intensity` is a per-junction
  mean-queue-depth knob; the draw is seeded (deterministic).
- **Prometheus / Grafana** `[ops]` — metrics scraper / dashboard. The engine exposes
  `/metrics`; queue depth/wait are time-series for future panels.
- **rAF (`requestAnimationFrame`)** `[ui]` — the browser's per-frame callback; drives
  the live dead-reckoning redraw loop (Sprint 023).
- **resolver (fleet resolver)** `[sim]` — the step that fixes open-ended segments
  (queue slots) by folding all filed ships' junction arrivals in time order.
- **RMN / GSN / RHN (PN) / SLN / IAN** `[lore]` — the navies: Royal Manticoran /
  Grayson Space / Republic of Haven (People's) / Solarian League / Imperial
  Andermani.
- **run-out / approach** `[sim]` — the mundane n-space impeller legs out to the
  origin star's hyper limit and in from the destination's (not band climb/descent).
- **`ruff` / `uv` / `pytest`** `[ops]` — Python lint+format / package manager / test
  runner for the engine.
- **segment** `[sim]` — one closed-form piece of a route in absolute time. Kinds:
  `transit`, `layover`, `hyper_cruise`, `wormhole_queue`, `wormhole_transit`.
- **SI units** `[sci]` — metres/seconds internally; converted to km/AU/ly and
  human durations only at the API boundary.
- **SimClock** `[sim]` — the engine's only time source (epoch offset + rate). Prod
  runs rate 1.0; dev can jump/accelerate. Carries the PD calendar.
- **spectral type** `[sci]` — a star's classification (e.g. G0, G2V). Drives the
  hyper-limit lookup.
- **streak drive** `[lore]` — an advanced drive needed to reach the highest hyper
  band (Iota); recorded but not required on v1 clocks.
- **subjective time** `[sci]` — elapsed time aboard a relativistic ship vs outside
  (time dilation). Reported (`subjective_time_delta`), not simulated.
- **Svelte / SvelteKit** `[ui]` — the front-end framework (Svelte 5 + adapter-static
  SPA) for the Phase 2.5 UI.
- **`svelte-check` / Vitest** `[ops][ui]` — the UI type-checker / unit-test runner
  (folded into `just check` via `ui-check`).
- **terminus** `[lore]` — one end of a wormhole link, reached via a junction's nexus
  (e.g. the Beowulf Terminus of the Manticore Junction).
- **transit** `[sim]` — a segment kind: a closed-form n-space run (brachistochrone /
  accel-coast-decel) within a system.
- **transponder** `[proj][lore]` — a ship's canonical identity, the dotted
  `nation.class.hull` (plus an engine-only "modified" bit). See `nation.class.hull`.
- **T-year (Terran year)** `[lore][sim]` — a standard year used by the PD calendar
  conversions.
- **velocity multiplier** `[lore][sci]` — the factor a hyperspace band multiplies a
  ship's real velocity by to get apparent velocity (Weber's chart).
- **Warshawski sail** `[lore]` — the disk-shaped field ships deploy to ride hyper-
  space grav waves; does not negate per-band bleed-off for ordinary travel.
- **WebGL / PixiJS** `[ui]` — GPU 2D rendering; the documented escape hatch if the
  map ever needs more than Canvas-2D (not needed at current scale).
- **wormhole junction** `[lore]` — a nexus linking several distant termini; transit
  is near-instant but serializes through a queue (the destabilization buffer).
- **`wormhole_queue` / `wormhole_transit`** `[sim]` — segment kinds: waiting in a
  junction's queue (open-ended, resolver-fixed) then the instant translation.
- **zone mode** `[ui]` — a hotkey (`z`) that recenters + clamps the system view to a
  system (vs free zoom). "Zones" also = LOD clustering of crowded objects (later).
