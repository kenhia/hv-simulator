# Sprint 014 — Inter-system travel (Phase 2b, slice 2)

Builds the engine's **multi-mode execution** on the Sprint 013 DES core: a filed
route can now cross systems via **hyperspace** and **wormhole** legs, not just
in-system n-space hops. The headline deliverable is an end-to-end
**Sol → Beowulf → Manticore → Yeltsin's Star** flight with realistic multi-day
clocks, state queryable across systems. **No dynamic wormhole queue** (that's
2c) and **no automatic route-finding** — routes are hand-filed this sprint; the
`nav-planner` tool that produces them is Sprint 015.

## Goal

Teach the engine three travel modes and the leg→segment decomposition that turns
a filed multi-mode route into DES segments, reading all model parameters from the
universe artifact (hyper bands, per-star hyper limits, wormhole links + safety
buffer). Demonstrate the canonical interstellar run end-to-end.

## Decisions baked in (this session)

- **Engine modes only this sprint; nav-planner is 015.** Validate the multi-mode
  math against a *hand-filed* route before automating route-finding — the 013
  pattern (prove the substrate, then build on it).
- **Deliverable exercises every mode:** Sol →(hyper)→ Beowulf (`sigma-draconis`)
  →(wormhole, Beowulf Terminus)→ Manticore →(hyper, canon 31 ly)→ Yeltsin's Star.
- **Parameters come from the artifact, never hardcoded** (founding principle):
  apparent band velocity (`hyperspace_bands`), per-star `hyper_limit_lmin`,
  wormhole links + `transit_model.buffer_normal_s`. The engine stays a
  configurable physics box.
- **One representative cruise band for v1** (configurable), read from the data;
  multi-band optimisation ("fast lanes") stays deferred per the plan.
- **The DES seam from 013 is where the new kinds plug in** — extend the
  closed-kind set + exhaustive dispatch; no core rewrite.

## The leg→segment decomposition

A filed **route** is an ordered list of mode-tagged legs from an origin
`(system, body)`. The compiler walks them against the `Universe`, emitting DES
segments:

- **n-space leg** (within a system) → a `transit` segment (existing
  brachistochrone/coast solver). The **coast phase finally fires** here on legs
  long enough to hit the velocity cap (binary star-to-star, long in-system).
- **hyper leg** (system A → system B) → **three** segments:
  1. `transit` **climb** — impeller run from the current point out past system
     A's primary `hyper_limit_lmin`, arriving at ≤ the band's
     `entry_velocity_limit_c` (translation constraint).
  2. `hyper_cruise` (new kind) — straight-line across the inter-system distance
     at the band's `apparent_velocity_c`; time = distance / apparent velocity.
  3. `transit` **descent** — impeller run from system B's hyper limit inward to
     the target body.
- **wormhole leg** (junction link A → B) → a `wormhole_transit` (new kind):
  near-instant translation **+ fixed `buffer_normal_s`** clearance. No dynamic
  queue (2c).

## Scope

### 1. Engine: artifact accessors (`hvsim.universe`)
- Expose `hyperspace_bands`, `hyper_limits` / per-star `hyper_limit_lmin`, the
  `transit_model` (buffer), and the wormhole links as a routable adjacency the
  compiler can read. Pure reads over the existing read-only artifact.

### 2. Engine: new DES segment kinds (`hvsim.des`)
- Add `hyper_cruise` and `wormhole_transit` to `SEGMENT_KINDS` + the
  `evaluate`/`segment_end` dispatch. Both are closed-form (fixed `t_end`); they
  use the resolver seam's *shape* but need no resolver.
- `hyper_cruise` reports position along the galactic-frame line between systems;
  `wormhole_transit` is a short fixed-buffer segment bridging the two termini.

### 3. Engine: cross-system state representation
- `ShipState` gains enough context to answer "where, and in which system" across
  a multi-system trip (e.g. a `system` field; a frame indicator for the
  interstellar leg). In-system phases unchanged; `hyper_cruise` reports a
  galactic-frame position. **Document the frame convention.**

### 4. Engine: multi-mode route + compiler
- A filed multi-mode `Route` (ordered mode-tagged legs) and a `compile_route`
  that emits the DES segment sequence above; `state(T)` runs it on the core.
- The single-system `FlightPlan`/`compile_plan` path keeps working (a route with
  only n-space legs ≡ today's plan).

### 5. Deliverable + demonstration
- Hand-file **Sol → Beowulf → Manticore → Yeltsin's** and show realistic
  multi-day clocks + cross-system `state(T)` (a test plus a `just`-runnable demo
  or CLI). Each mode covered by focused unit tests (climb-to-limit geometry,
  hyper_cruise timing, wormhole buffer, coast firing).

## Out of scope

- **Nav route planner** — Sprint 015 (`tools/nav-planner/`, UI-first).
- **Wormhole queue / phantom traffic / the `tau(M)` destabilisation model** —
  Phase 2c. 2b uses only the fixed buffer.
- **Multi-band route optimisation, grav waves / sail-riding** — deferred ("fast
  lanes / weather").
- **Relativity simulation** — `subjective_time_delta` stays *reported*, not
  simulated (Phase 1 rule).
- **Full HTTP filing of multi-mode routes + persistence** — keep the deliverable
  engine-level (test/CLI/demo); HTTP/DB surface for multi-mode plans is a
  follow-on unless it falls out cheaply. (Note it; don't force it.)
- **`ALLOW_ANACHRONISMS` / temporal validity** — later.

## Tasks

- [x] Universe accessors: hyperspace bands, per-star hyper limit, transit-model
      buffer, routable wormhole adjacency (pure reads).
- [x] DES: add `hyper_cruise` + `wormhole_transit` kinds with exhaustive
      dispatch; closed-form `segment_end`/`evaluate`.
- [x] `ShipState` cross-system context (system + frame for the interstellar leg);
      document the frame convention; in-system behaviour unchanged.
- [x] Multi-mode `Route` + `compile_route` (leg→segment decomposition); the
      n-space-only path stays equivalent to `compile_plan`.
- [x] Hand-filed **Sol → Beowulf → Manticore → Yeltsin's** demo (test + a
      `just` recipe / CLI) showing multi-day clocks and cross-system state.
- [x] Unit tests: climb-to-limit (uses artifact `hyper_limit_lmin` + band entry
      limit), hyper_cruise timing (distance / apparent velocity from data),
      wormhole buffer, **coast fires** on a long n-space leg, determinism.
- [x] `just check` green (engine + tools); CLAUDE.md + plan updated.

## Acceptance criteria

- The engine executes a hand-filed multi-mode route end-to-end on the DES core:
  **Sol → Beowulf → Manticore → Yeltsin's** compiles into the expected segment
  sequence (n-space climb / `hyper_cruise` / descent per hyper leg;
  `wormhole_transit` for the Beowulf Terminus) and `state(T)` answers
  position/phase/system across the whole trip with **realistic multi-day clocks**.
- All band speeds, hyper limits, and the wormhole buffer are **read from the
  artifact** — grep shows no hardcoded values.
- `hyper_cruise` time = inter-system distance / band apparent velocity;
  `wormhole_transit` = instant + `buffer_normal_s`; the **coast phase fires** on
  a long n-space leg (a regression-worthy first).
- The single-system Earth → Titan → Earth plan still behaves identically
  (Phase 1 + 013 parity preserved). Determinism holds.
- `just check` green. Universe artifact + contract unchanged (v0.1.1) unless a
  real need surfaces.

## Notes / decisions

- **Frame handling is the main new design call.** In-system positions stay
  heliocentric (per-system SI metres); the interstellar `hyper_cruise` reports a
  **galactic-frame** position. `ShipState` carries which frame/system applies so
  a caller (and the future UI) can interpret it. Keep it explicit, not implicit.
- **Translation constraint:** a ship may only translate into a band at ≤ that
  band's `entry_velocity_limit_c` (Alpha = 0.3c, instantly fatal above). The
  climb profile must arrive within the limit; note where this bounds the climb.
- **Why hand-filed routes now:** the planner's value depends on these modes being
  correct first. Filing one canonical route by hand is trivial next to general
  graph search and lets us validate the multi-mode math against a known answer.
- **2c seam preserved:** `wormhole_transit` uses a fixed buffer now; swapping in
  the `tau(M)` queue resolver later is a `segment_end` change at the seam 013
  built — not another re-founding.

## Outcome

Done. New `hvsim.route` package: a filed multi-mode `Route` (mode-tagged legs)
compiles via `compile_route` into DES segments — a hyper leg → n-space **climb**
to the origin star's `hyper_limit_lmin` + `hyper_cruise` (distance ÷ band
apparent velocity) + **descent** to the target body; a wormhole leg →
`wormhole_transit` (instant + `buffer_normal_s`). New `hvsim.universe` accessors
(`hyperspace_bands`/`hyperspace_band`, `hyper_limit_lmin` with the Sol=G2
special-case, `transit_model`, `wormhole_link_between`, `coordinates`) feed it —
every parameter read from the artifact, none hardcoded.

DES gained `hyper_cruise` + `wormhole_transit` kinds (exhaustive dispatch
extended); `Segment` moved to `des/segment.py` (its natural home) and grew the
inter-system fields; `ShipState` gained `system` + `frame` (heliocentric per
system; **galactic** for the interstellar leg). `flightplan` re-exports `Segment`
and sets `system="sol"` — Phase 1 + 013 parity intact (all prior tests
unchanged).

**Deliverable runs:** `just demo-route` flies **Sol →(hyper)→ Beowulf
→(wormhole)→ Manticore →(hyper, 31 ly)→ Grayson** — six segments, **~130-day**
clock (73 d + 56 d hyper cruises, ~5-7 h impeller climbs/descents, 300 s wormhole
buffer), phase/system/frame reported across the whole trip. New
`tests/test_route.py` (8) covers the decomposition, hyper-cruise timing, the
climb-from-hyper-limit, the wormhole buffer, the galactic-frame interstellar
state, arrival in the destination system, **coast firing** on a ~149 AU n-space
leg, and determinism. `just check` green (**90 engine tests** + all tools).
Contract unchanged (v0.1.1). Nav route-finding is Sprint 015.
