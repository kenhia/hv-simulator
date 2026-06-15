# Sprint 013 — DES core re-founding (Phase 2b, slice 1)

Opens **Phase 2b**. Re-founds the engine's execution layer on a **lazy,
deterministic discrete-event simulation (DES)** core — the substrate every later
mechanic (inter-system travel, the wormhole queue, combat) sits on. This sprint
adds **no new travel**: the bar is **byte-for-byte parity** with today's Phase 1
single-system behavior, proving the new model reproduces the old one with zero
drift before anything is built on it.

Per `planning/006` (decision #3, *DES-core-first*): retrofitting the core later
is exactly the "start over" we're avoiding, and the DES model costs little even
when no queues exist yet — so we build it first and put 2b on it.

## Goal

Stand up the DES core (`hvsim.des`) — an event queue + lazy `advance-to-T` +
an extensible segment/event/mode model — and re-express the canonical
**Earth → Titan Station → Earth** flight plan on it. `state(T)` becomes
"deterministically replay events up to T, then evaluate the active segment
analytically." Acceptance = the DES path matches the existing analytic
`state_at` across a dense sweep of T, and the existing API behaves identically.

## Decisions baked in (this session)

- **Slice 1 is the core + parity only.** No `hyper_cruise`, no
  `wormhole_transit`, no nav planner — those are slice 2 (Sprint 014). This
  de-risks the re-founding against a known-good oracle (Phase 1).
- **Keep the math.** `ephemeris`, `kinematics`, `SimClock` port essentially
  verbatim (006's "keep the libraries" — ~40% ports as-is). What changes is the
  engine's *shape*, not its physics.
- **Model for extensibility now, even though parity needs none of it.** The
  segment/event/mode kinds are a closed, explicitly-enumerated set with
  exhaustive dispatch (a `match`/registry that fails loudly on an unhandled
  kind) — this is the seam where 2c's wormhole-queue resolver and an eventual
  Rust port's enums slot in. Build the *shape* that admits open-ended,
  resolver-fixed segment boundaries; leave the resolvers themselves for 2c.
- **PD calendar (small, in-scope).** Extend `SimClock` with a PD ↔ T-year ↔
  epoch mapping anchored at **1890 PD** (the decided sim epoch). Pure and needed
  by every travel sprint; kept tightly bounded so it doesn't dilute the parity
  focus. `ALLOW_ANACHRONISMS` + temporal-validity enforcement stay deferred
  (they matter when rosters/eras do — Phase 2c/3).

## Scope

### 1. The DES core (`engine/src/hvsim/des/`)
- **Event queue** — a time-ordered (heap) structure of `(t, event)`; ties broken
  deterministically (stable secondary key, e.g. ship id + seq) so replay is
  reproducible.
- **Segment/event/mode model** — closed, enumerated kinds. Today's kinds are
  `transit` and `layover` (closed-form). The model must *structurally* allow a
  segment whose `t_end` is fixed by a resolver at arrival (open-ended), even
  though no such segment exists yet. Exhaustive dispatch over kinds.
- **Lazy advance-to-T** — process events in time order until the next event time
  exceeds T, then evaluate the active segment analytically. Sparse events (one
  per boundary); no per-tick loop (still forbidden).
- **Determinism** — `state(plans, universe, seed, T)` is a pure function; same
  inputs + same T → same world. Snapshots/memoization, if any, are a perf detail
  with no semantic effect.

### 2. Re-express Phase 1 execution on the core
- Feed the existing `compile_plan` segments into the DES core (or have the core
  produce them) so the single-system flight plan runs as a degenerate
  event sequence (deterministic boundaries, no resolver).
- `state(T)` via the core replaces / wraps the current `state_at` internals; the
  HTTP API's observable behavior is unchanged.

### 3. PD calendar on `SimClock`
- Add PD-year ↔ T-year ↔ epoch conversion (anchor 1890 PD); expose it where the
  clock is read. No behavior change to rate/jump.

## Out of scope

- **Any new travel mode** — `hyper_cruise`, `wormhole_transit`, the
  climb-to-hyper-limit leg, multi-system routes (Sprint 014).
- **The nav route planner** — lands in Sprint 014 as a **separate tool**
  (`tools/nav-planner/`), not in the engine; designed toward the eventual UI flow
  (select a ship → pick a destination → planner emits a flight plan for user
  approval). Noted in the plan now; not built here.
- **Wormhole queue / phantom traffic / resolvers** — Phase 2c (the core just has
  to *admit* them structurally).
- **`ALLOW_ANACHRONISMS` enforcement / temporal validity** — later.
- **Rust port** — the model must be stable first (2c checkpoint).

## Tasks

- [x] `hvsim.des` core: event queue (deterministic ordering), segment/event/mode
      model (closed kinds + exhaustive dispatch, structurally admits open-ended
      boundaries), lazy `advance_to(T)`.
- [x] Re-express the Earth → Titan → Earth plan on the core; route engine state
      queries through it (API behavior unchanged).
- [x] Extend `SimClock` with PD ↔ T-year ↔ epoch (anchor 1890 PD).
- [x] **Parity test**: DES `state(T)` matches analytic `state_at` for the
      canonical plan across a dense T sweep (position/velocity/phase), within
      float tolerance; document the tolerance.
- [x] **Determinism test**: same `(plans, universe, seed, T)` → identical state;
      replay order is stable.
- [x] `just check` green (engine + tools); CLAUDE.md notes the DES core; plan
      updated (Phase 2b sub-split + nav-planner-as-tool decision).

## Acceptance criteria

- A `hvsim.des` core exists with a deterministic event queue, an extensible
  (closed-kind, exhaustively-dispatched) segment/event model that *structurally*
  allows resolver-fixed open-ended boundaries, and a lazy `advance_to(T)` with
  **no per-tick loop**.
- The canonical **Earth → Titan Station → Earth** plan runs on the core and its
  `state(T)` **matches the Phase 1 analytic `state_at`** across a dense T sweep
  (documented float tolerance) — zero drift. Existing API tests stay green
  unchanged (the parity proof) plus the new parity + determinism tests.
- `SimClock` converts PD ↔ T-year ↔ epoch (1890 PD anchor); existing clock
  behavior (rate/jump) unchanged.
- No new travel modes introduced; the universe artifact + contract are untouched
  (still v0.1.1). `just check` green.

## Notes / decisions

- **Why parity-only is the right first slice:** the design risk in 2b is the
  *event model*, not the language or the travel math. Proving the model
  reproduces a known-good oracle (Phase 1) before layering `hyper_cruise` /
  queues onto it is the cheapest place to catch a modeling mistake.
- **The seam for 2c:** "open-ended segment, fixed by a resolver at arrival" is
  the wormhole queue's shape. Building the core so that shape is *expressible*
  now (without implementing a resolver) is what keeps 2c from being another
  re-founding.
- **Nav planner as a separate tool (decided):** keeps the founding split — the
  engine executes filed routes, never computes them. Built UI-first in intent so
  it later backs "pick ship → pick destination → approve plan." Slice 2.
- Carries 006's library-keep / shape-change split and the 1890 PD epoch.

## Outcome

Done. Built `hvsim.des` — `event.py` (deterministic `Event`/`EventQueue`,
min-heap keyed on `(t, order)`), `model.py` (closed `SEGMENT_KINDS` +
exhaustive `evaluate`/`segment_end` dispatch, with `segment_end` as the
resolver seam that raises `OpenEndedSegment` for an unset `t_end`), and
`core.py` (`Simulation` + the moved `ShipState`; lazy `advance_to(T)` pops
boundary events in time order and stops at the first past `T`; `state(T)`
replays then evaluates the active segment). No per-tick loop.

`flightplan.state_at` now delegates to `Simulation` via `simulation_for`;
`ShipState` is sourced from `des` and re-exported (public API unchanged). The
DES core imports only `ephemeris`/`kinematics` (no flightplan import → no cycle);
segments are consumed duck-typed.

`SimClock` gained the PD calendar: `to_pd`/`from_pd`/`pd_now` + a
`pd_epoch_year` field (default 1890.0) and module `T_YEAR`; `now()`/rate/jump
unchanged.

**Parity proven** two ways: (1) all 69 prior tests pass unchanged — the API and
flightplan suites now run through the DES path; (2) a new `tests/test_des.py`
(13 tests) asserts `Simulation.state` matches a *frozen pre-DES analytic oracle*
across a 300-point dense T sweep and at every segment boundary (positions to
abs=1e-6 m — identical float ops, so bit-equal; phase/seq/eta exact), plus
determinism (field-for-field equality, query-order independence), event-queue
ordering, exhaustive-dispatch rejection (`UnknownSegmentKind`), the open-ended
seam (`OpenEndedSegment`), and the PD calendar. `just check` green (82 engine
tests + all tools). Universe artifact + contract untouched (v0.1.1).
