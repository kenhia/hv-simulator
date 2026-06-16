# Sprint 015 — Hyperspace band model + ship/class tech-data model

Phase 2b **supplemental** (inserted 2026-06-16). Replaces Sprint 014's
single-band placeholder with David Weber's **canonical** hyper-band speed chart,
makes a ship's FTL speed depend on its **max safe band** and type, and fixes the
ship/class data model so per-ship **overrides** (upgrades / mods / damage) are
expressible. Lock the band math **first**, then apply it to ship classes.

## Source of truth (found this session)

David Weber's own "Effective Speed By Hyper Band" chart (June 2009, posted to
davidweber.net; the live page is gone, archived at
`web.archive.org/web/20210507101710/https://davidweber.net/posts/15-hyperband-graph.html`,
captured with notes in `.scratch/david-weber-hyper-band-chart.md`). This is
**canon** and supersedes our earlier interpolation.

| Band | Translation bleed-off | Velocity multiplier | Warship (×c) | Merchant (×c) |
|---|---|---|---|---|
| Alpha | 92% | 62 | 37.2 | 31.0 |
| Beta | 85% | 767 | 460.2 | 383.5 |
| Gamma | 78% | 1473 | 883.8 | 736.5 |
| Delta | 72% | 2178 | 1306.8 | 1089.0 |
| Epsilon | 66% | 2884 | 1730.4 | 1442.0* |
| Zeta | 61% | 3589 | 2153.4 | 1794.5* |
| Eta | 56% | 4294 | 2576.4 | 2147.0* |
| Theta | 52% | 5000 | 3000.0 | 2500.0* |
| Iota | 48% | 6000 | (currently unattainable) | (currently unattainable) |

**The model is `apparent_velocity_c = velocity_multiplier(band) × real_velocity_c`**,
where the chart's two columns bake in reference real velocities **warship 0.6c /
merchant 0.5c** (every cell = multiplier × 0.6 or × 0.5; e.g. Theta 5000 × 0.6 =
3000, × 0.5 = 2500). It reproduces the in-book datapoints (Epsilon 1442, Zeta
~2500 at 0.7c, etc.). *(The scratch capture has a typo — Delta warship is 1306.8,
not 1206.8; use the multiplier 2178.)*

## Decisions baked in (this session)

- **Use the chart verbatim.** Per-band `velocity_multiplier` + `translation_bleed_off`
  are canon; reference real velocities are warship 0.6c / merchant 0.5c. No
  compensator / PD-date speed scaling (keep it simple — Ken's call). Iota is
  era-gated (below); interpolate its effective-×c only if/when a ship may use it.
- **Bleed-off is real — the Warshawski sail does *not* negate it for ordinary
  travel** (verified: the sail article is about grav-wave sailing + power, not
  band-translation penalties; the Fandom "negated both" line is grav-wave-specific).
  Record the per-band bleed-off. **v1 models steady cruise speed precisely;**
  the bleed-off/crash-translation cost is recorded and hooked, not fully simulated.
- **Normal (non-crash) translation at a configurable `0.2c` constant**; crews
  tolerate it. **Crash translations are a future combat hook**: a flight plan will
  later carry a `tactical` tag that recomputes with crash numbers (Navy trades
  crew strain for speed). Not built this sprint — just the constant + the seam.
- **Ship tech data lives in the CLASS; a ship may override fields** (accel,
  armament, max band, …) for upgrades/mods/damage. **Effective stats = class ⊕
  ship overrides.** Every ship must have a class; a classless ship gets an
  auto-created **singleton class** (named for the ship, `singleton: true`) — a
  future guard for "adding a 2nd ship to a singleton → rename the class?".
- **Band capability lives in the data; era/nation caps are anachronism-gated.**
  A class's `max_hyper_band` is its *actual* capability. **Iota+** needs the
  **streak drive** (not present in our dataset) → practical max is **Theta**; we
  simply don't assign Iota. **No temporal era enforcement this sprint** —
  `ALLOW_ANACHRONISMS` is effectively *true* (the pre-combat default), so ships
  use their capability and our Alliance-era hulls fly freely in the 1890 clock.
  Temporal/nation caps — e.g. **Grayson capped at mid-Gamma *pre-Alliance*** —
  are recorded as flavor but apply only later under `ALLOW_ANACHRONISMS = false`
  (deferred). Our current Grayson classes are Alliance-era, so they get their real
  (higher) bands now.
- **Band-climb time is noise we don't model.** Translating up through bands to
  reach the cruise band takes time + bleeds speed, but over interstellar distances
  it's negligible. v1 enforces only the **≤0.3c translation** at the n-space↔hyper
  boundary; the hyper leg then cruises at the ship's **max-band** numbers
  immediately (no band-by-band climb, no bleed-off applied to travel time). The
  bleed-off figures are recorded in the data for canon completeness + the future
  tactical/crash path, not applied to v1 clocks.

## Scope

### 1. Lock the band model (data + contract) — do this first
- Transcribe the chart into `data/hyperspace/hyperspace.json`: per-band
  `velocity_multiplier` (canon) and `translation_bleed_off_pct` (canon); the
  reference real velocities (warship 0.6c / merchant 0.5c); Iota `unattainable`.
  Replace the old interpolated `nominal_c` with the multiplier model (or keep it
  as a derived convenience). Cite the davidweber.net archive + the in-book
  datapoints it reproduces.
- A short validation: the model reproduces the canon (real, apparent) pairs
  (Epsilon 1442, Zeta 2500@0.7c, …). Capture in the data notes or a planning note.
- **Attribution (`data/README.md`):** record where the chart was found
  (the davidweber.net archive link) and that the page marks it
  `Copyright (c) 2009-21 Word of Weber, LLC - All Rights Reserved`. Add a note
  that **once the simulation reaches v1.0.0+, an effort will be made to obtain
  authorization** to use the data (with a complete description of the project +
  screenshots) — distinct from the rest of `data/`'s CC BY-SA wiki-derived text.
- **Contract:** `hyperspace_bands` gains `velocity_multiplier` +
  `translation_bleed_off_pct`; add the reference velocities + non-crash
  translation constant where the model globals live. **Minor bump → v0.2.0.**

### 2. Ship / class tech-data model (apply the band model)
- `ship_classes`: add `max_hyper_band` (band order) + `singleton`; classify
  warship-vs-merchant → real cruise velocity (proposed rule: a class with a
  `navy` / military `hull_classification` cruises 0.6c, civilian 0.5c —
  overridable). Canon-flag `max_hyper_band` (mostly inferred; canon hints:
  warships commonly **Zeta**, couriers ride **Theta**, merchants ~**Delta**).
  Grayson Alliance-era classes get their real (higher) bands; the **pre-Alliance
  mid-Gamma cap is anachronism-gated** (deferred, not applied here).
- `ships`: an **override** mechanism (nullable override fields / an overrides
  blob) so a hull can shadow class stats (incl. `max_hyper_band`, acceleration,
  armament). Compiler resolves **effective stats = class ⊕ overrides**.
- **Tooling guard** (compiler/validator): every ship has a class; a classless
  ship auto-creates a `singleton: true` class named for it. (The "2nd ship to a
  singleton" rename-prompt is a later UX nicety — for now warn.)
- **Contract:** the above `ship_classes` / `ships` columns.

### 3. Engine applies the model
- `Universe`: accessors for the band multiplier/bleed-off + globals, and
  **effective ship stats** (class ⊕ override) incl. `max_hyper_band`.
- `route.compile_route`: `hyper_cruise` apparent speed =
  `multiplier(ship max_band) × ship_real_cruise_velocity` — drop the single-band
  Alpha default; cruise at the max-band numbers immediately (no band-climb time).
  Enforce only the alpha-translation `0.3c` ceiling (the run-out already arrives
  ≤0.3c); the `0.2c` non-crash translation is the named constant. Leave the
  crash/tactical path + the bleed-off (recorded, unapplied) as documented hooks.

### 4. Demo + tests
- `just demo-route` now reflects ship band: a fast warship reaches Grayson far
  quicker than a freighter (different `max_hyper_band` / real velocity).
- Tests: the chart reproduces the canon datapoints; `apparent = multiplier ×
  real`; effective-stat resolution (a ship override beats its class);
  singleton-class auto-creation + "every ship has a class"; band gating (a
  Gamma-limited ship cruises slower than a Theta ship over the same leg).

## Out of scope

- **Crash translations / tactical routing** — future combat (just the constant +
  the `tactical` seam this sprint).
- **`ALLOW_ANACHRONISMS` temporal/nation enforcement** (incl. the Grayson
  pre-Alliance mid-Gamma cap, `date_introduced_pd` windows) — deferred; recorded
  as flavor only. Ships use their capability this sprint.
- **Band-climb time / applying bleed-off to clocks** — treated as noise; only the
  0.3c translation limit is enforced.
- **Compensator / PD-date speed scaling**, Kappa band — skip (Ken's call).
- **Grav-wave sailing, the Tellerman wave, "fast lanes"** — still deferred.
- **Nav route planner** — Sprint 016.
- **The "rename a singleton on 2nd ship" UX prompt** — later; warn for now.

## Tasks

- [x] **Lock the band math:** transcribe Weber's chart into `hyperspace.json`
      (multiplier + bleed-off, canon; ref velocities 0.6/0.5; Iota gated);
      validate it reproduces the in-book datapoints. Contract bump → v0.2.0.
- [x] `ship_classes`: `max_hyper_band` + `singleton`; warship/merchant → real
      cruise velocity rule; band assignments inferred by hull (canon:false).
- [x] `ships`: override mechanism; compiler resolves effective stats = class ⊕
      override; enforce every ship has a class; auto-singleton for classless.
- [x] Engine: band accessors + effective-stat accessors; `compile_route` uses
      `multiplier(max_band) × real_velocity`; crash/tactical left as a hook.
- [x] `just demo-route` varies by ship; tests per the list above.
- [x] `just check` green (engine + tools); `just contracts` green; CLAUDE.md +
      plan + galaxy-changelog + data README updated.

## Acceptance criteria

- The band model is **Weber's chart, encoded as data** (`apparent = multiplier ×
  real`), reproducing the canon datapoints; bleed-off recorded per band; reference
  velocities + the 0.2c non-crash + 0.3c alpha limits are constants, not magic
  numbers.
- A ship's hyper speed derives from its **effective `max_hyper_band`** (class ⊕
  override) and type (real cruise velocity); a higher-band ship demonstrably beats
  a lower-band one on `demo-route`. Iota is never assigned (no streak drive); no
  temporal era enforcement this sprint.
- **Every ship resolves to a class**; a classless ship auto-creates a
  `singleton: true` class; a per-ship override shadows its class stat.
- Contract is re-frozen at **v0.2.0**; `just check` + `just contracts` green;
  Sol + the 014 deliverable still fly (now with realistic per-ship band speeds).

## Notes / decisions

- **Bleed-off can be a *feature*, not just a cost** (Ken): a warship willing to
  crash-translate can stay under impeller closer to the limit, then dump velocity
  — a pro/con the future `tactical` path can exploit. We record bleed-off now so
  that path is cheap later.
- **Crew effects:** canon is clearest on the Alpha↔n-space translation; a
  plausible generalisation is `apparent_speed × bleed_off`, but numbers are thin.
  v1 bakes a single non-crash translation speed (**0.2c**, a named constant) used
  by merchants *and* Navy in normal ops; Navy "crash" is the later tactical tag.
- **Why class-primary + overrides:** the dataset already keeps tech on the class
  consistently; what's missing is representing an individual hull that differs
  (e.g. `gsns-andrew-massengil` with a compensator upgrade overriding its Honor
  Harrington-class `max_g`). Overrides add exactly that without duplicating class
  data.
- **Size:** this is a larger sprint (band model + data-model refactor + engine).
  It's kept together because `max_hyper_band` is the bridge between them and we're
  in the registry anyway; can split (band-model / data-model) if it runs long.

## Outcome

Done. Encoded Weber's chart into `data/hyperspace/hyperspace.json`
(per-band `velocity_multiplier` + `translation_bleed_off_pct`, canon; the
`apparent_velocity_model` block with warship 0.6c / merchant 0.5c references, the
0.2c non-crash + 0.3c alpha constants, validation against the in-book datapoints,
and the davidweber.net-archive + copyright provenance). Special-attribution note
added to `data/README.md` (chart is "All Rights Reserved"; authorization to be
sought at v1.0.0+).

**Contract → v0.2.0:** `hyperspace_bands` now carries the multiplier/bleed-off
(replacing `apparent_velocity_c`); new `hyperspace_model` globals row;
`ship_classes` gains `max_hyper_band` (+canon flag) / `real_cruise_velocity_c` /
`singleton`; `ships` gains sparse `ovr_*` override columns and `class_id` is now
NOT NULL. The compiler derives `max_hyper_band` from hull type (warships Zeta/Eta,
merchants Delta — canon:false, overridable), sets cruise velocity from the
warship/merchant rule, auto-creates a singleton class for a classless hull, and
rejects an unknown `class_id`.

Engine: `Universe.hyperspace_model` + `effective_ship` (COALESCE override over
class); `Ship` gained `max_hyper_band` / `hyper_cruise_velocity_c`;
`compile_route` cruises at `multiplier(ship max band) × real velocity`, rejects an
unattainable band; `ship_from_artifact` builds a route Ship from a hull's
effective stats. Band-climb time + bleed-off are recorded but not applied to
clocks (only the 0.3c limit); nation/era caps await `ALLOW_ANACHRONISMS`.

`just demo-route` now flies the canonical route for two hulls: **HMS Nike
(Eta) ≈ 11.1 d** vs **CMS Starhauler (Delta) ≈ 26.2 d** (was a flat 130 d).
Tests: engine `tests/test_route.py` (12 — band model, galactic-frame cruise,
higher-band-is-faster, unattainable-band rejection, run-to-limit, wormhole buffer,
effective-stat override resolution, coast, determinism); compiler tests add
singleton auto-create + unknown-class rejection + band-model compile checks.
`just check` (94 engine + tools) and `just contracts` (16 tables) green.
