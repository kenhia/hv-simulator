# Sprint 017 — Transponder ship identity

A focused foundation sprint (Phase 2b.1, *operate the galaxy*): give every ship a
canonical **transponder ID** that maps to its technical data, before the API
integration (Sprint 018) builds the deployed galaxy service on top of it. The
transponder is the identity the dashboard/UI shows, the engine resolves to stats,
and Phase 3 combat/narrative will key off (false-flag spoofing included — deferred
to wartime). Realizes the kwi #65 "transponder + vector" idea.

## The scheme (decided this session)

A transponder is the dotted **`nation.class.hull`** of stable integer codes, plus
an **engine-only `modified` bit** (a 4th component, never displayed):

- **`nation`** — stable code per star nation; **0 = unaffiliated** (for ad-hoc /
  user ships). **Not sequential** (sequential codes read as obviously synthetic):
  **1 = Sol** (the Solarian homeworld), **2 = Beowulf** (humanity's first colony
  out), and every other nation a hand-picked **random-ish code in [42, 999]** for
  a lived-in feel. (Revisit the range once it's >~50% full.)
- **`class`** — stable code per ship class (numbered within its nation).
- **`hull`** — stable code per ship within its class.
- **`modified`** — `0`/`1`, **derived** (1 iff the hull carries any `ovr_*`
  override from Sprint 015); tells the engine this hull deviates from class stats.
  Engine-only — not in the displayed transponder.

**Representation: integer components + a formatted string** (decided) — store the
codes as columns; expose the display transponder as `f"{nation}.{class}.{hull}"`.
A packed `uint32` "squawk" is a trivial future derived form; not built now.
**Supplement, not replace** (decided): the human slug ids (`hms-nike-bc-562`,
`solarian-league`) stay primary keys for authoring/debugging; transponder codes
are added as the canonical runtime/display identity.

**Codes are assigned once and never renumbered** (transponders are identities).
Nation + class codes are authored in the data (few, meaningful, stable); hull
codes are assigned per class. The compiler validates uniqueness.

## Scope

### 1. Numbering (data)
- Author a stable **`code`** on each nation — **0** unaffiliated, **1** Sol,
  **2** Beowulf, the rest **random-ish in [42, 999]** (not sequential) — and on
  each ship class (unique within its nation). Add a reserved **generic class** +
  the unaffiliated nation (code 0) so ad-hoc / user ships have a home. Codes are
  hand-authored (stable, controlled) and never renumbered.
- Assign **`hull_code`** per ship (unique within its class).
- A short note in `data/README.md` on the scheme + the never-renumber rule.

### 2. Contract + compiler
- `nations.code`, `ship_classes.code`, `ships.hull_code` (+ derived `modified`,
  and a stored display `transponder` string for convenience). **Contract bump
  → v0.3.0.**
- Compiler: read the codes, derive `modified` from `ovr_*`, compute the
  transponder, and **validate** uniqueness (nation codes unique; class codes
  unique within nation; hull codes unique within class) — fail loudly on a
  collision or a missing code.

### 3. Engine resolution
- `Universe`: `transponder(ship_id) -> str`, `ship_by_transponder(code) -> dict`,
  and `effective_ship` reachable by transponder — so the identity maps to the
  effective (class ⊕ override) technical data. A small format/parse helper
  (`"n.c.h"` ↔ components).
- Tests: round-trip (ship → transponder → effective stats); `modified` reflects an
  overridden hull; unaffiliated/generic ad-hoc ship resolves; uniqueness holds
  across the real artifact.

## Out of scope

- **False-flag / spoofing** (squawking a different transponder) — wartime; noted,
  deferred. Peacetime ships squawk true.
- **Packed `uint32`** squawk value — future derived form.
- **Replacing slug ids** — supplement only.
- **Route / planner / API adoption** of transponder ids — **Sprint 018** (the
  API-integration sprint wires filing/state/fleet to transponders).
- **"Vector"** — already available (a ship's current velocity from `ShipState`);
  transponder + vector composes for free in 018's state/fleet output.

## Tasks

- [x] Data: nation/class codes in `data/transponder-codes.json` (0 = unaffiliated,
      1 Sol, 2 Beowulf reserved, rest random-ish); `data/README.md` note.
- [x] Contract → **v0.3.0**: `nations.code`, `ship_classes.code`, `ships.hull_code`,
      derived `modified` + display `transponder`.
- [x] Compiler: post-stub `_assign_transponders` pass — codes + `modified` +
      transponder string; validates uniqueness + missing codes (fail loudly).
- [x] Engine `Universe`: `transponder` / `ship_by_transponder` /
      `effective_ship_by_transponder` + `parse`/`format_transponder`; tests.
- [x] `just check` (engine + tools) + `just contracts` green; CLAUDE.md + plan +
      galaxy-changelog + data README updated.

## Acceptance criteria

- Every ship in the artifact has a unique transponder `nation.class.hull`; the
  engine resolves a transponder → that hull's effective technical data; `modified`
  is set iff the hull overrides its class.
- Ad-hoc / unaffiliated ships are representable (nation 0 + generic class).
- Slugs remain the primary keys (non-breaking); contract re-frozen at **v0.3.0**;
  `just check` + `just contracts` green. No route/API behavior change yet.

## Notes / decisions

- **Why first:** identity is load-bearing for the API (018), the dashboard/UI, and
  Phase 3 (combat/narrative + false-flag). Getting it canonical now avoids
  retrofitting the integration.
- **`nation` vs operator:** the transponder's nation is the class's affiliation
  (the numbering hierarchy). A hull operated by a *different* nation (a capture, or
  false-flag) is a wartime nuance — deferred; peacetime operator == affiliation.
- **Stability over convenience:** codes never renumber. New nations/classes/hulls
  take the next free code; the compiler enforces uniqueness so a clash is caught at
  build, not in flight.

## Outcome

Done. `data/transponder-codes.json` holds the stable nation + class codes
(non-sequential nations: 0 unaffiliated, 1 Sol/Solarian League, 2 Beowulf
*reserved*, others hand-picked in [42,999]); hull codes are assigned per class by
the compiler. A post-stub **`_assign_transponders`** pass (runs after stubbing, so
every nation/class/ship exists) sets the codes, derives `modified` from `ovr_*`,
computes the `nation.class.hull` transponder, and **validates uniqueness + missing
codes** (build error). Contract → **v0.3.0** (`nations.code`, `ship_classes.code`,
`ships.hull_code`/`modified`/`transponder`).

Engine `Universe` gained `transponder` / `ship_by_transponder` /
`effective_ship_by_transponder` (+ `parse_transponder`/`format_transponder`); a
transponder resolves straight to the hull's effective (class ⊕ override) stats,
and `modified` flags an overridden hull. Slug ids remain primary keys.

All **33 ships got unique transponders** (e.g. `emerald-dawn` = `1.1.1`, SLNS
*Nevada* = `1.2.3`, GNS *Honor Harrington* = `213.1.1`); Beowulf's `2` is reserved
(unused, pending a Republic of Beowulf nation — kwi #66). Tests: engine
`test_transponder.py` (5 — lookup, resolution, modified shadows class, parse/format)
+ compiler (real-data uniqueness/codes + a synthetic modified/missing-code unit).
`just check` (103 engine + all tools) + `just contracts` green. No route/API
behavior change — routes/API adopt transponders in Sprint 018.
