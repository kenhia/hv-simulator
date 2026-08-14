# Honorverse-Data review — Phase 2 data integration

*Reviewed 2026-06-14. Source dataset: `/gratch/Honorverse-Data/` (a staging area
feeding `hvsim` as it expands beyond Sol). This is analysis + planning, not a
sprint spec.*

## TL;DR

The dataset is **well-built and already designed around hvsim** — canon flags
per fact, orbital element names that mirror `ephemeris/elements.py`, stations
using `rides_on` (= our `Station(parent=...)`), and ships whose acceleration
blocks answer an open question in our own plan. It is the **seed for the Phase 2
universe builder and the Phase 3 combat sim**, not just lore. The work to consume
it is mostly *extensions* to hvsim (binary primaries, a route graph, a PD
calendar, temporal validity), plus a one-time **orbit-derivation pass** because
canon fixes planet *order* but almost no orbital *geometry*.

## What's there (first cut, 2026-06-13)

| Layer | Files | Notes |
|---|---|---|
| Schemas | `star-system`, `ship-class`, `ship` (JSON Schema 2020-12) | element names align with hvsim |
| Systems | manticore (binary, 14 bodies/3 belts/7 places), yeltsins-star (Grayson), basilisk, endicott | physical: stars/planets/moons/belts/places |
| Nations | star-kingdom-of-manticore (+ refs to protectorate-of-grayson, masada) | political: territory, termini, capitals |
| Ships | 9 classes, 23 named ships | RMN, Grayson, Havenite navies |
| Pipeline | `.claude/skills/honorverse-{system,ship}-scribe` | repeatable wiki→JSON via MediaWiki API |

Provenance is careful: CC BY-SA 3.0 attribution, per-page source table, and the
**`canon` convention tracked per fact** (`canon:true` existence vs a nested
`orbit{canon:false, determined:false}` placement). This is exactly the
distinction we need — it tells the sim what's real vs. what we're free to invent.

## How it already maps to hvsim

- **Bodies/moons/stations** → `ephemeris` `Elements` / `Moon` / `Station`. The
  `orbit` block fields (`a_au, e, i_deg, L_deg, long_peri_deg, long_node_deg,
  period_days`) are named to drop onto our Keplerian machinery; `rides_on`
  matches `Station(parent=...)`.
- **Ship classes** → `flightplan.Ship`. The `acceleration` block gives
  **`normal_g` (cruise, with compensator margin) and `max_g` (emergency)** — and
  notes the canon **80% margin** (`normal = 0.8 × max`). **This is the answer to
  open question #5** in `planning/004` (compensator/cruise-vs-max accel): the
  data hands us both numbers per class. Our seed range (100–700 g) is validated —
  real classes span **~487 g (Havenite Warlord) to ~678 g (Grayson Raoul
  Courvosier II / Manticoran Nike)**; couriers sit at the top, walls a bit lower.
- **Relational graph**: ship → `class_id` → `affiliation_nation_id` → nation →
  `capital_system_id` / system. Clean foreign keys; a loader can resolve them.

## The interesting finding: the binary is where our coast code finally fires

Manticore is a **binary** (A: G0, 1.12 M☉; B: G2, 0.92 M☉) with the two stars
**~78–99 AU apart** (separation 650–827 light-minutes, e≈0.12; 1 lm = 1.7988e10 m).
Bodies orbit one star or the other.

Our velocity cap (0.6c) only engages on a brachistochrone past
`d > v_max²/a ≈ 88 AU` (noted in `004`, tested only *synthetically* in Sprint 003
because nothing in Sol is that far). **Manticore A↔B is right at that threshold:**
at periastron (~78 AU) a 250 g hop is a pure brachistochrone (~40 h, peak ~0.57c);
at apastron (~99 AU) it crosses 0.6c and the **coast phase actually engages** for
the first time in the project. The cross-subsystem run is a genuine ~1–2 day
normal-space voyage — exactly the "days" timescale Phase 2 promised, and it
exercises code we wrote months ago and never ran for real.

## Gaps / extensions hvsim needs to ingest this

1. **Binary primaries (biggest physics gap).** hvsim assumes a single
   heliocentric primary. A system needs *per-star* frames: bodies resolve around
   their `parent_star`; the two stars orbit a barycenter. The `binary` block
   already captures the inputs. Generalize "heliocentric" → "system-centric"
   (each system its own coordinate island).
2. **Orbit-derivation pass (one-time, non-canon).** Almost every `orbit` is
   `null`. Canon constrains a few (Manticore year = 1.73 T-yr → period → `a` via
   Kepler from A's mass; belt ordering; body order). We must invent the rest,
   set `determined:true`, keep `canon:false`. Good first job for a "universe
   builder" tool — or a scripted Kepler pass.
3. **Route graph + wormholes.** The Manticore Junction has **7 canon termini**
   (Beowulf, Trevor's Star, Hennesy, Gregor, Basilisk, Matapan, Lynx) as
   directed edges to other systems. This is the seed for the Phase 2 route graph
   and the `wormhole_transit` / `wormhole_queue` segment kinds. The sim consumes
   *edges* (distance/mode/queue), so it may not need absolute galactic coords for
   travel at all — only for a galaxy map.
4. **PD calendar.** Dates are Post-Diaspora years (founded 1485 PD … Oyster Bay
   1922 PD); hvsim runs on J2000/UTC. Need a PD↔T-year↔epoch mapping (and
   "T-year" = standard Terran year is already the unit bridge).
5. **Temporal validity.** Stations carry lifecycle (`status:destroyed`,
   `destroyed_pd:1922`; `under_construction`, `built_pd`); ships carry `fate_pd`.
   A body/place/ship exists only in a time window. hvsim has no notion of an
   object existing-as-of-T yet — worth a small `valid_from/valid_to` concept so a
   query at a PD date returns the right roster.
6. **Asteroid belts** (3 in Manticore) — a new display/economic body type;
   not needed for routing, but the schema has them.
7. **ID namespacing.** Body ids are bare within a system file (e.g. Manticore-B
   VI is `titan`) — which **collides with Sol's `titan`/Titan Station**. The
   loader must namespace ids by system (e.g. `manticore:titan`) before merging
   into one registry.

## Mapping to the project phases

- **Phase 2 (universe builder, hyperspace, wormholes):** this dataset *is* the
  universe-builder's content (or its hand-curated seed). systems + nations +
  junction termini → the system catalog and route graph the README of `004` calls
  for. The scribe skills make expansion cheap (add Andermani, Solarian, Havenite
  systems on demand).
- **Phase 3 (navies, combat, narrative):** ship-classes (armament `by_arc`,
  weapon-code legend, magazines/missile-pods, crew) are ready-made **combat-sim
  inputs**; ships + nations give order-of-battle and per-polity navies for the
  admiral agents.
- **Now-ish flavor:** the compensator 80% margin (open Q#5) could land earlier as
  a cruise-vs-max accel on `Ship`, independent of Phase 2.

## Risks / watch-items

- **License (share-alike).** Derived data incorporating CC BY-SA 3.0 wiki text
  must stay BY-SA and attributed. The `lore`/`summary` free-text fields are the
  copyrightable part; keep `ATTRIBUTION.md` with any distribution. Bare facts
  (a planet's name/type) aren't copyrightable, but don't strip attribution.
- **Canon-false everywhere in orbits.** Whatever we derive is *our* invention —
  keep it flagged so a future canon source can override without ambiguity.
- **Source tags need novel verification** (the `HH<n>` etc. tags are transcribed
  from wiki citations; treat as secondary until checked).
- **Unresolved canon** noted in-data (HMSS Vulcan/Weyland parent bodies; the
  GNS/GSNS prefix inconsistency) — fine to carry as flagged uncertainty.

## Recommended next steps (when Phase 2 starts)

1. **Decide the loader boundary**: a separate universe-builder service owns this
   data (per `004`'s architecture split); the sim ingests a *compiled* system +
   route graph, not raw wiki JSON. Keep the physics engine dumb.
2. **Orbit-derivation utility** (non-canon): Kepler from stated masses +
   constraints (Manticore 1.73 T-yr), filling `orbit` blocks → `determined:true`.
   Reuse `ephemeris._orbital_to_xyz`.
3. **Generalize the ephemeris to system-centric / binary primaries**; add a
   `parent_star` dimension to body resolution.
4. **Model the route graph** (systems as nodes; junction termini + hyperspace
   lanes as edges) and add `wormhole_transit`/`hyper_cruise` segment kinds — the
   sim still just executes segments.
5. **Add a PD calendar + object temporal validity** so state queries at a PD date
   return the era-correct roster (pre/post Oyster Bay, etc.).
6. **Namespace ids on load** to avoid Sol/Manticore collisions.

## Open questions for Phase 2 planning

- Does the universe builder live in its own repo/service (likely), and is this
  dataset its input or its output format?
- Galactic coordinates: invent a convention (origin/axes) for a 3D map, or stay
  edge/graph-based for travel and skip absolute coords for now?
- How far do we model the binary — true two-body barycentric motion, or treat each
  subsystem as independent with a fixed A–B offset for v1?
- Where does "as-of PD year" live — a sim-clock epoch mapping, or a universe-layer
  query parameter?
