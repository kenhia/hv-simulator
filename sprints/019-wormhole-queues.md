# Sprint 019 — Wormhole queues (the DES payoff)

Phase 2c. The **first stateful resolver** on the DES core: a ship reaching a
wormhole junction joins a **queue**, and its transit slot is fixed at arrival from
the junction's dynamic state — not knowable at filing time. This is what turns the
engine from a calculator into a true simulator (the reason for the 013
re-founding). Engine/CLI-level this sprint; the deployed `/fleet` board shows
queue positions in **Sprint 020**.

## Goal

A ship transiting a busy junction reports **"#3 in queue, transit in 12:27"**, and
as sim time advances counts down **#3 → #2 → #1 → pops through**. Queue depth
**varies** with each junction's traffic, and **real ships interleave** with each
other and with phantom traffic — all deterministic.

## The mechanic (from the artifact)

- A junction transit destabilises the nexus for `interval = max(tau(M), buffer)`
  seconds (`tau(M) = A·√M + B·M²`, M = tons transited; `transit_model` coeffs +
  `buffer_normal_s`). The junction is unusable during that interval → transits
  **serialise into a queue**.
- A ship's wait = (remaining current interval) + Σ interval(ship ahead); then it
  transits (instant) and busies the junction for its own interval.

## Design

### Open-ended segment + resolver (the 013 seam)
- A wormhole leg compiles to: run-up to the junction (n-space) → an **open-ended
  `wormhole_queue` segment** (`t_end = None`) → `wormhole_transit` (instant). The
  resolver fixes the queue segment's `t_end` = the ship's transit-open time. This
  is exactly the `OpenEndedSegment`/`segment_end` hook the DES core was built with.
- `segment_end` for a queue segment consults **junction/world state** (phantom +
  other ships), so resolution moves from per-segment to a **fleet-level** step.

### Phantom traffic (per the refined plan)
- Each junction carries a **traffic-intensity knob** (data; fabricated). On a real
  ship's arrival, the **phantom ships ahead** are drawn from a distribution with
  that knob as its **mean** — so depth varies (quiet → transit ~immediately; busy
  → #27). The draw (count + each phantom's mass) is a **pure function of
  `(junction, arriving-ship key, seed)`** → reproducible, never a constant #3.

### Real-ship interleaving (deterministic)
- A ship's **arrival time at a junction is queue-independent** (it's just the
  run-up segments), so all ships' junction arrivals are well-defined before any
  queue is resolved — no circularity. Resolve junction-transit events in **global
  time order**: the earliest arrival across all filed ships resolves first (fixing
  its slot + shifting its own downstream), then the next. A ship's *downstream*
  junctions couple through its own earlier waits.
- A ship's queue position = (real ships ahead by arrival time) + (phantom ahead).
  Near-simultaneous real arrivals break ties on a **stable key** (arrival instant,
  then transponder) → total, reproducible order (your A #3 → B ≥ #4).

### Determinism
- `state(filed routes, universe, seed, T)` is a pure function — same inputs + same
  T → same queues, always. The seed + the per-junction knob are the only sources
  of "randomness"; everything folds deterministically.

## Scope

### 1. Data + contract
- Per-junction **traffic-intensity knob** in `data/wormholes/wormhole-network.json`
  (canon:false; e.g. Manticore Junction busy, Erewhon quieter) → `wormhole_junctions`
  column. A global **sim seed** constant. **Contract bump → v0.4.0.**

### 2. Engine: the queue resolver (`hvsim/queue/`, consumed by a fleet-level step)
- Phantom-traffic generator (seeded; count+masses per arrival from the knob).
- The junction queue: serialise ahead transits through `interval = max(tau(M),
  buffer)`; compute a ship's **transit-open** time + **position(T)**.
- A **fleet resolve** that takes the set of filed routes + universe + seed, folds
  all junction-transit events in global time order, and fixes every open-ended
  `wormhole_queue` segment (real ships interleave; downstream junctions shift).
- `compile_route` emits the open-ended queue segment; `segment_end`/state resolve
  it via the fleet step (supersedes 014's fixed-buffer `wormhole_transit`).

### 3. State + countdown
- A queued ship's `ShipState` reports phase **`queued`** + **queue position** +
  **transit ETA**. Position decrements as ahead transits clear (the countdown).
- A `just`-runnable demo (extend `demo-route` or a new `just queue-demo`): a ship
  (or two) through a busy junction, printing "#N … pops".

### 4. Tests
- `tau`/interval math; single-ship phantom queue + countdown; **two real ships
  interleave** (A #3 → B ≥ #4); depth **varies** by junction knob + seed (not a
  constant); a quiet junction → ~immediate transit; determinism (same
  routes+seed+T → identical); the open-ended segment now resolves (no
  `OpenEndedSegment` raise on a queue leg).

## Out of scope

- **Deployed `/fleet` queue display + the live "#3 … pops" board** — Sprint 020
  (API/ops; the resolver lands first).
- **Knob auto-tuning from measured real traffic** — later (the note's "as we
  evolve"); v1 uses fabricated per-junction knobs.
- **Mass-transit / Condition-Zulu buffers, emergency transit** — later; v1 uses
  the normal buffer + `tau(M)`.
- **Combat** (the next resolver) — Phase 3.

## Tasks

- [x] Data + contract: per-junction traffic knob + sim seed; `wormhole_junctions`
      column; **v0.4.0**; compiler + `validate-data`/tests updated.
- [x] `hvsim/queue/`: phantom-traffic generator + the junction queue (interval
      serialisation, transit-open, position).
- [x] Fleet-level resolve: open-ended `wormhole_queue` segments fixed by global
      time-ordered folding of real + phantom transits; `compile_route` emits them;
      `segment_end`/state resolve via the fleet step.
- [x] `ShipState` `queued` phase + position + transit ETA; `just queue-demo` countdown demo.
- [x] Tests per the list above; `just check` + `just contracts` green.
- [x] **Rust-port checkpoint** (below); CLAUDE.md + plan + changelog updated.

## Acceptance criteria

- A ship through a busy junction reports `queued` with a position + transit ETA;
  position counts down to transit ("#3 → … → pops"), all on the DES core (no
  per-tick loop).
- Queue depth **varies** with the junction knob + seed (a quiet junction can be
  ~immediate; a busy one deep); **two real ships interleave deterministically** by
  arrival (A #3 → B ≥ #4).
- `state(routes, universe, seed, T)` is reproducible. The single-system Earth →
  Titan plan + the 014/015 interstellar deliverables still fly (a no-queue leg ≈
  the old instant+buffer). `just check` + `just contracts` green; contract v0.4.0.

## Notes / decisions

- **Engine-first** (decided): the resolver is the hard, architectural part; the
  deployed board is a thin follow-on (020). Real-ship interleaving is **in v1**
  (decided) — it's the DES's whole reason for being (006).
- **Architectural step:** resolution moves from per-ship `Simulation` to a
  **fleet-level** fold (all routes share junction state). The per-ship `state(T)`
  still answers analytically once queues are fixed; the fold is the new piece.
- **Rust-port checkpoint:** with the resolver/state-machine now accreting (queues
  → combat next), revisit "port the engine to Rust?" Record the call (likely
  *not yet* — Python velocity still high, model still moving) with reasons.

## Rust-port checkpoint — decision (recorded)

**Call: not yet.** Stay in Python through Phase 2c/3a; revisit when the model
stops moving (post-combat) or a real perf/correctness wall appears. Reasons:

- **The model is still moving.** This sprint reshaped the segment kinds, added a
  fleet-level fold, and changed the wormhole leg's structure — exactly the churn a
  port would have to chase. Combat (the next resolver) will move it again. Porting
  now would freeze a still-fluid design in the slower-to-iterate language.
- **The contract already buys the optionality.** The artifact DDL + engine OpenAPI
  are the language-agnostic seam (frozen per minor version); a future Rust engine
  reads the same `universe.db` and serves the same API. So the port stays cheap to
  start *later* — there's no first-mover cost to deferring.
- **No perf pressure.** State is analytic (no per-tick loop) and the fleet fold is
  O(transits) over a handful of ships; nothing is hot. Determinism is already
  enforced in tests, so a port would be a faithfulness exercise, not a rescue.
- **What would flip it:** the exhaustive-match discipline (the `match` on segment
  kinds, the closed `SEGMENT_KINDS`) genuinely wants compile-time checking once the
  kind set is large/stable; combat-grade numeric throughput; or a second team/
  language consuming the core. Re-evaluate at the **end of Phase 3a (combat)**.
