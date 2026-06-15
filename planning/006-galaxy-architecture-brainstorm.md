# 006 — Galaxy-scale architecture brainstorm

*2026-06-14. Response to `XXX-expanding-to-galaxy.md` (your notes), synthesizing
`005-honorverse-data-review.md` and the data-side planning now in
`/gratch/Honorverse-Data/planning/` + `hyperspace/` + `wormholes/`. This is a
thinking/decision doc, not a sprint spec.*

## The one sentence that reframes everything

You put your finger on it: **the wormhole queue breaks "compile the whole plan
up front, then answer `state_at(T)` analytically."** A ship's transit-departure
isn't knowable when the plan is filed — it depends on the junction's dynamic
state when the ship *arrives*. That single fact is what pushes us from a
stateless calculator to a real **simulator**. Everything below follows from it.

The good news: this does **not** mean throwing away the math, and it does **not**
mean a continuous game loop (still forbidden). It means adopting the right model
for "events that resolve in time order" — a **discrete-event simulation (DES)** —
which is a small, principled step from where we are.

## Recommended core model: lazy, deterministic discrete-event simulation

Keep the soul of Phase 1 (no per-tick loop, zero drift, reproducible) while
admitting the statefulness queues need:

- **Segments stay closed-form** where they can (n-space accel/coast/decel — the
  coast phase finally earns its keep on binary/interstellar legs; hyper cruise;
  layovers). `ephemeris` and `kinematics` port essentially verbatim.
- **Some segment boundaries become events** resolved by a stateful *resolver* at
  the moment the ship reaches them. The wormhole queue is the first such
  resolver; combat is a later one. A "wait in queue" segment is **open-ended**
  until its resolver fixes the departure time.
- **`state(T)` = deterministically replay events up to T, then evaluate the
  current segment analytically.** Events are sparse (one per segment boundary),
  so this is cheap even for thousands of ships. No continuous tick; we advance
  *event-to-event*, lazily, on query.
- **Determinism is preserved** by making everything a pure function of *(filed
  plans, universe data, a fixed seed, T)*. Phantom junction traffic is a seeded
  process; the queue order is the deterministic result of folding arrivals in
  time order. Same inputs + same T → same world, always. Snapshots/memoization
  are a performance detail, not a semantic one.

This is the key insight: we move from "closed-form per segment" to "deterministic
replay to T," which keeps *reproducibility and no-drift* while allowing *stateful
mechanics*. It also generalizes cleanly to Phase 3 combat (resolve a battle at an
event time; feed results back as new segments/state).

### Why not the alternatives

- **Pure analytic + fake it** (each ship sees only phantom traffic, ignores other
  real ships): keeps today's model, but real-ship-behind-real-ship interactions
  never emerge, and it won't generalize to combat. A dead end we'd rewrite.
- **Persisted advancing world + background tick**: the obvious "real simulator"
  shape, but it reintroduces drift, ordering bugs, and the loop we banned. The
  lazy-replay DES gets the same behavior with none of that.

## What ports, what gets re-founded

This answers your "start over?" question: it's **re-found the engine, keep the
libraries.** Roughly 40% ports as-is; the flight-plan/execution layer is rebuilt.

| Keep (port) | Re-found / new |
|---|---|
| `ephemeris` (extend to per-system + **binary** primaries) | DES core (event queue, lazy advance-to-T) |
| `kinematics` (Vec3, profile/trajectory/intercept) | Multi-mode flight plan: n-space ↔ hyper ↔ wormhole |
| `SimClock` (extend with PD calendar) | Stateful **resolvers** (wormhole queue first) |
| `units`, the Sol-map UI concept | **Galactic frame** + multi-system world model |
| `flightplan.state_at` *idea* (now replay-to-T) | **Route execution** (graph of systems/edges) |

The math is gold and stays. What changes is the engine's *shape*: from "compile →
analytic lookup" to "load a universe → execute filed routes via deterministic
event replay."

## Architecture (preserving the load-bearing split)

The original separation — **physics dumb, world-building smart** — gets *stronger*
here, not weaker:

```
┌─ Data / Universe builder (Python + the scribe skills) ───────────────┐
│  scrape → systems/ nations/ ships/ wormholes/ hyperspace/            │
│  + NEW tools: coordinate-frame solver, orbit-derivation,             │
│    universe-compiler (assemble+validate+resolve FKs+namespace ids)   │
│  → emits a single compiled "universe artifact" (the engine's input)  │
└──────────────────────────────────────────────────────────────────────┘
                                 │  (JSON universe artifact)
┌─ Nav / route planner ──────────┴──────────────────────────────────────┐
│  graph search over systems+edges → an ordered multi-mode route        │
│  (NOT physics; stays out of the engine, per the founding principle)   │
└───────────────────────────────────────────────────────────────────────┘
                                 │  (a filed route)
┌─ Simulator engine (Python now / maybe Rust later — see below) ────────┐
│  loads the universe; executes routes via the lazy DES;                │
│  owns trajectories, mode switches, the wormhole queue resolver;       │
│  answers "where is everything at T". The thing that becomes >         │
│  flight-plan+calc+API.                                                │
└───────────────────────────────────────────────────────────────────────┘
                                 │  (HTTP / state API)
┌─ UI (Phase 2.5) ───────────────┴──────────────────────────────────────┐
│  first-class web/GUI: switch systems, zoom, layer toggles, queues     │
└───────────────────────────────────────────────────────────────────────┘
```

Crucial discipline carried over: **the engine never computes routes** (the nav
planner does) and **never invents lore** (the data layer does). The engine reads
the queue formula coefficients, band speeds, and hyper-limits *from the data* —
it doesn't hardcode them. The dataset's `transit_model`, `hyperspace.bands`, and
hyper-limit table are inputs, keeping the engine a configurable physics box.

## The language question (your big revisit)

Performance is **not** the driver — the lazy DES is cheap at this scale (sparse
events, thousands of ships is nothing). So "Rust for speed" isn't the argument.
The real argument for Rust is **correctness of a growing state machine**:
exhaustive enums for segment/event/mode kinds, `match` that fails to compile when
a case is missed, ownership that makes illegal states unrepresentable. For an
engine that will accrete queues → combat → economies, that rigor pays off (and
you flagged the learning interest).

Against: a blind rewrite spends the rewrite cost on an *unproven* design, and our
velocity in Python is high (math done, FastAPI/SQLAlchemy wired).

**Recommendation — polyglot, with a hedge that keeps the choice reversible:**

1. **Tools & data pipeline stay Python.** The scribes are already Python; orbit
   derivation, frame triangulation, and the universe-compiler are math/IO glue
   Python is great at. No reason to move them.
2. **Prototype the DES engine in Python first** — reuse the existing math, prove
   the event model + queue resolver + multi-mode plans cheaply. This is where the
   design risk is, not the language.
3. **Define the boundaries as language-agnostic contracts now**: a JSON Schema
   for the *universe artifact* and an OpenAPI spec for the *engine API*. With
   those frozen, the engine is a black box behind HTTP — so a later **Rust port
   of just the engine** disturbs neither the Python tools nor the UI.
4. **Port the engine to Rust when (and if) the model is stable** and the
   type-rigor is worth it. Treat Rust as a deliberate v2, not a prerequisite.

Net: you get the right tool per task (your instinct), avoid betting the rewrite on
an unvalidated design, and keep the door open to Rust by making the engine
swappable at a clean seam.

## The keystone the data team already flagged: the coordinate frame

Their `002 #1` is correct — a fabricated **Sol-origin, +Z galactic-north** frame
is the backbone for the general case. But their `003` worked example is the
nuance that de-risks us: **many specific routes have canon pairwise distances**
(Manticore↔Yeltsin's 31 ly) and are flyable *today* without the frame. So:

- Build a **coordinate-frame solver** (Python tool) that triangulates canon
  bearings+distances into XYZ, stored `canon:false`. It unblocks the general
  hyperspace case and any galaxy map.
- But the engine should **prefer a canon pairwise distance when one exists**, and
  fall back to frame-derived distance otherwise. That lets us demonstrate
  inter-system flight before the frame is perfect.

## Time, calendars, and a time-varying universe

- **PD calendar**: extend `SimClock` to map PD years ↔ T-years ↔ the epoch. Pick
  a canonical "present" PD year for the first galaxy cut.
- **Temporal validity** (stations destroyed/built, ship `fate_pd`): the universe
  itself changes over time. For v1, resolve the roster *as of the chosen present
  year* and defer full time-travel-through-eras. Worth designing the data model
  for it (`valid_from/valid_to`) even if the engine only uses "now."

## The wormhole queue (the feature that's worth the rebuild)

The data layer already handed us a usable, book-grounded model: `interval(M) =
max(tau(M), buffer)` with `tau(M)=A√M + B·M²`, normal/emergency/Condition-Zulu
buffers, and clean queue semantics (a ship's wait = remaining current interval +
Σ interval ahead). The engine implements exactly this as the first **resolver**:

- On arrival at a junction, a ship joins the queue; its transit-open time is
  computed from the junction's busy-until timeline + ships ahead.
- **Phantom traffic** (seeded, deterministic per junction) supplies "ships ahead"
  so queues feel alive *now* — your "SS Tankersley is #3, transit in 12:27 …
  #2 … #1 … *pops to Basilisk*" payoff — without needing thousands of tracked
  ships. Model it as a seeded arrival process so it's reproducible and the
  dashboard countdown is stable.

This is the canonical example of why we need the DES core, and it's the single
most satisfying thing to build.

## Phase 2.5 — first-class UI

Agreed it deserves dedicated time once the engine is solid. Requirements to carry
forward (no design yet): a **galaxy/map view** (systems as nodes, wormhole edges,
ships in transit) that **drills into a per-system top-down** (today's Sol map,
generalized); **switch systems, zoom, layer toggles** (kwi #57's show/hide
generalizes here); **queue/ETA panels** at junctions; **time controls**. Keep it
a separate front-end on the engine API (web is the natural choice; a richer stack
than vanilla Canvas is fair game here). The dead-reckoning trick still applies for
smooth motion between polls.

## Suggested phasing (supersedes `004`'s Phase 2 sketch — for discussion)

- **2a — Universe foundation.** Coordinate-frame solver + universe-compiler;
  engine loads a multi-system catalog incl. **binary** primaries; reports body
  positions galaxy-wide. (Mostly Python tools + ephemeris extension.)
- **2b — Inter-system travel, no queue.** Nav route planner (n-space→hyper→
  wormhole), hyper band + hyper-limit model, multi-mode flight plans; wormhole
  transit as instant + fixed buffer. Demonstrable **Sol→Manticore→Yeltsin's**.
- **2c — The DES core + wormhole queues + phantom traffic.** The stateful
  re-founding; the queue payoff. **Language-port decision point** lands here.
- **2.5 — First-class UI.**
- **3 — Navies/combat/narrative** (resolvers generalize to combat).

Open sequencing question (below): do 2a/2b on the lazy-DES core *from the start*
(so we don't retrofit), or evolve the current engine for 2a/2b and re-found at 2c?
My lean: **build the DES core first** and put 2a/2b on it — retrofitting is the
"start over" you're trying to avoid, and the DES model costs little even when no
queues exist yet.

## New skills/tools to add (Python, in the data repo)

Beyond the existing system/ship/wormhole scribes: a **coordinate-frame /
triangulation** tool, an **orbit-derivation** tool (Kepler from the canon anchors:
Manticore 1.73 T-yr, Medusa ~7 lm, Grayson ~13.5 lm), a **universe-compiler**
(assemble + validate against schema + resolve FKs + namespace ids → the engine
artifact), and a **route/graph validator** (connectivity, dangling termini). A
**galactic-map builder** (render positions) feeds the UI.

## Decisions — resolved (2026-06-14)

1. **Engine model: lazy deterministic DES.** ✅ Adopted.
2. **Language: Python now.** Stay Python until we *need* otherwise. When ready,
   make the explicit call "switch to Rust? which parts?" (likely engine-only —
   keep it open). De-risk by freezing the boundary contracts (universe-artifact
   schema, engine OpenAPI) so an engine-only port stays cheap.
3. **Sequencing: DES-core-first.** ✅ 2a/2b are built on the DES core, not
   retrofitted.
4. **Repo & build layout:** monorepo-style — `tools/<toolname>/` (each its own
   `pyproject.toml`, or `Cargo.toml` if a tool ever goes Rust), `data/` for the
   dataset, build orchestrated by a script + `justfile` recipes. See
   *Data storage* and *Repo & build layout* below for the details this raised.
5. **Scope fence / epoch:** start the sim at **1890 PD** (peacetime, ~a decade
   before *On Basilisk Station*); advance toward **~1905 PD** when combat lands.
   Single "present" PD year + canon pairwise distances (frame as fast-follow);
   defer grav waves / sail-riding / eras. See *Epoch & anachronisms* below.

## Data storage: authored JSON → compiled SQLite artifact

Resolving the "should the data live in a DB?" question: **both, with distinct
roles.**

- **Source of truth stays JSON** (per-file, git-diffable, PR-reviewable). This is
  where the value lives: per-fact `canon` flags, CC BY-SA attribution, and
  scribe-generated diffs you can eyeball. A SQLite blob in git would forfeit
  review, diffs, and clean attribution — a regression.
- **Runtime store is a compiled SQLite "universe artifact"** (= the artifact this
  doc already proposed, made SQLite). The **universe-compiler** reads the JSON,
  validates against schema, resolves FKs (`system_id`, `class_id`, termini),
  namespaces ids (the Sol/Manticore `titan` collision), and writes a read-only
  SQLite the engine loads.

Net: the **engine never touches loose JSON**, so "JSON gets hard to add to" stops
being an engine problem — it's only an authoring concern (handled by the scribes,
schema validation, and small editor CLIs if hand-tuning derived orbits/coords
gets tedious). Relational integrity + graph queries at runtime; human-friendly
authoring + review at edit time. SQLite is already in our toolchain. Flip JSON→DB
*as source* only if we'd rather hand-edit in a DB UI than in files — at the cost
of git review, which for provenance-sensitive canon data isn't worth it.

## Repo & build layout

Your layout preference, made concrete (and a good fit since we're re-founding the
engine anyway — natural moment to restructure):

```
hv-simulator/                 (monorepo)
  engine/        the simulator (Python now; could become a Rust crate later)
  tools/<name>/  each tool its own pyproject.toml (scribes migrate here from
                 /gratch/.claude/skills; + frame-solver, orbit-derive,
                 universe-compiler, route/graph-validator, map-builder)
  data/          dataset JSON source of truth (+ compiled artifact output)
  ui/            Phase 2.5 front-end
  justfile       build/sync/validate/compile/deploy recipes across the workspace
```

**One thing to confirm — licensing.** The code is **MIT**; the dataset carries
**CC BY-SA 3.0** (wiki-derived `lore`/`summary` text). Monorepo is fine, but the
`data/` subtree must keep its own CC BY-SA `LICENSE` + `ATTRIBUTION.md`
(per-directory licensing) so the two don't bleed together. Alternative is keeping
`data/` + its scribes as a separate repo (clean license split, contract at the
artifact boundary) — but that cuts against your single-`justfile` build-all
preference. **DECIDED (2026-06-15): monorepo with per-directory licensing** —
code MIT, `data/` carries its own CC BY-SA 3.0 `LICENSE` + `ATTRIBUTION.md`.

Per the founding split, the **nav route planner** is *not* physics — it sits with
the tools/data side (or its own service), and the engine only *executes* a filed
route. (Carried from the architecture diagram above.)

## Epoch & anachronisms

- **Sim epoch: 1890 PD.** Peacetime, ~a decade before *On Basilisk Station*
  (1900 PD). `SimClock` extends with a PD↔T-year↔epoch mapping; 1890 PD is the
  anchor. A later phase advances the "present" toward ~1905 PD as combat and
  newer ship classes come online (a deliberate clock jump, not a tick).
- **`ALLOW_ANACHRONISMS` core setting** — couples to the temporal-validity model
  (objects carry `valid_from`/`valid_to`, e.g. a class's `date_introduced_pd`, a
  station's `destroyed_pd`, a ship's `fate_pd`):
  - `true` → the engine ignores temporal windows; *any* ship/class/station is
    usable regardless of build/destroy dates. **Default pre-combat** (lets us
    populate the galaxy freely while building).
  - `false` → the engine enforces existence-as-of the sim PD year. **Default once
    combat lands** — but always settable, so the original *Fearless* can still fly
    in an otherwise-canon-correct 1905 PD galaxy.
  This makes the flag the switch between "sandbox" and "canon-consistent" worlds,
  and it's the practical handle on the time-varying-universe problem 005/006
  raised.

## Open boundary work this implies (early, because contracts must be frozen)

Because the language call is deferred to a clean engine-only port, the
**boundary contracts become load-bearing now**: (1) the **universe-artifact**
schema (the compiled SQLite shape) and (2) the **engine HTTP API** (OpenAPI).
Freezing these early is what keeps "Python now, maybe Rust later" cheap.

## What I deliberately left out (agreeing with the data team)

Gravity waves, the Tellerman wave, Warshawski sail-riding, dimensional shear
beyond the hyper-limit rule, combat, and economies — all real, none required for
a *navigable galaxy with realistic clocks*. They become "fast lanes / weather"
and Phase 3 later.

## What I deliberately left out (agreeing with the data team)

Gravity waves, the Tellerman wave, Warshawski sail-riding, dimensional shear
beyond the hyper-limit rule, combat, and economies — all real, none required for
a *navigable galaxy with realistic clocks*. They become "fast lanes / weather"
and Phase 3 later.
