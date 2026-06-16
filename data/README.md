# Honorverse Data (incoming)

Staging area for structured Honorverse astrographic data, feeding the
[`hv-simulator`](https://github.com/kenhia/hv-simulator) (`hvsim`) as it expands
beyond the Sol System.

Primary source: the David Weber novels. Secondary source: the
[Honorverse Wiki](https://honorverse.fandom.com) (CC BY-SA 3.0 — see
[`ATTRIBUTION.md`](ATTRIBUTION.md)).

## Layout

```
Honorverse-Data/
  README.md
  ATTRIBUTION.md                       license + source citations
  schema/
    star-system.schema.json            JSON Schema (draft 2020-12) for system files
  systems/
    manticore-system.json              the physical star system (stars, planets, stations)
  nations/
    star-kingdom-of-manticore.json     the political entity (references systems by id)
```

## Two layers: systems vs. nations

A deliberate split, because one maps cleanly to the simulator and the other does
not:

- **`systems/`** — the *physical* thing the simulator places and routes ships
  through: stars, planets, moons, asteroid belts, and in-system "visitable
  places" (stations, shipyards, the wormhole junction).
- **`nations/`** — the *political* thing: which systems a star nation owns, its
  termini, naval stations, and protectorates. These reference systems by
  `system_id`.

This is why **Hancock Station** lives in the *nation* file, not the Manticore
system file: it sits in the separate, otherwise-uninhabited **Hancock System**.
When a `systems/hancock-system.json` is created, Hancock Station becomes a
`place` within it, and the nation file's reference still resolves by id. The same
holds for Basilisk/Medusa, Trevor's Star/San Martin, the Junction termini, etc.

## The `canon` convention (the important part)

Every mapped object carries a boolean **`canon`** flag:

- `canon: true` — established in the source material (novels or wiki).
- `canon: false` — **invented or derived by us** to fill a gap the canon leaves
  open (exact orbits, coordinates, separations not stated in the books).

Crucially, canon is tracked **per fact, not per object**. A planet's *existence*
is canon while its *orbit* is not — so each body has its own object-level `canon:
true` and a nested `orbit` block with its own `canon: false`:

```jsonc
{
  "id": "manticore", "name": "Manticore", "canon": true,   // the planet is canon
  "orbit": { "canon": false, "determined": false, "a_au": null, ... }  // its placement is not
}
```

`determined: false` + `null` values mean "needs to be filled." When you invent a
value, set the value, keep `canon: false`, and set `determined: true`.

### What canon actually gives us for Manticore

Very little hard orbital data. Canon establishes:

- System is **512 ly galactic-north of Sol**; binary G0 (1.12 M☉) + G2 (0.92 M☉).
- Barycentric distances (333 / 406 light-minutes) and separation range
  (650–827 light-minutes, e≈0.12).
- The **ordering and identity** of all 14 planets, named moons, and 3 belts.
- A Manticoran year = **1.73 T-years** (constrains Manticore's orbit).

It does **not** give semi-major axes, eccentricities, inclinations, or the
mutual orbital period. All of those are `canon: false` placeholders to be
derived (e.g. via Kepler's third law from the stated masses) or hand-tuned.

## Hyperspace band model — special attribution

The hyper-band speed numbers in [`hyperspace/hyperspace.json`](hyperspace/hyperspace.json)
(per-band velocity multiplier, translation bleed-off, and the warship/merchant
effective-times-c columns) come from **David Weber's own chart**, "Effective
Speed By Hyper Band" (posted 2009-06-03, collected by Joe Buckley):

- Source (archived; the live page is gone):
  <https://web.archive.org/web/20210507101710/https://davidweber.net/posts/15-hyperband-graph.html>
- The page marks the chart **"Copyright (c) 2009-21 Word of Weber, LLC - All
  Rights Reserved"** — i.e. *not* CC BY-SA like the wiki-derived text in this
  dataset.

These figures are used here as factual canon for a **non-commercial fan
simulation**. **Once `hv-simulator` reaches v1.0.0 or higher, an effort will be
made to obtain authorization** to use this data — at which point we can present a
complete description of the project (with screenshots, etc.). Until then this note
records the provenance and the rights status. If authorization is declined, these
specific numbers would be replaced with our own interpolated model.

## Transponder codes

[`transponder-codes.json`](transponder-codes.json) holds the **stable** integer
codes behind each ship's transponder (`nation.class.hull`, + an engine-only
`modified` bit). **Never renumber an assigned code** — transponders are
identities; new entities take a new, unused code. Nation codes are deliberately
**non-sequential**: `0` unaffiliated, `1` Sol (Solarian League), `2` Beowulf
(reserved for the Republic of Beowulf), all others a hand-picked random-ish value
in `[42, 999]`. Class codes are unique within a nation; **hull codes are authored
per ship** in `ships/ships.json` (unique within class, so the `nation.class.hull`
triple is unique). `just validate-data` (in `just check`) enforces that. (False-flag
/ spoofing is a wartime feature — deferred.)

## Units & conventions

- Stellar masses in **solar masses** (`mass_solar`).
- Binary separations in **light-minutes** (`_lmin`); 1 lm = 1.798754748e10 m.
- System distance from Sol in **light-years** (`distance_ly`).
- Orbital elements named to match the hvsim ephemeris (`a_au`, `e`, `i_deg`,
  `L_deg`, `long_peri_deg`, `long_node_deg`, `period_days`).
- Dates in **PD** (Post Diaspora) years, as in canon. "T-year" = standard
  Terran year.
- Stations use `rides_on` (the body they're fixed to), matching the simulator's
  `Station(parent=...)` model.

## Schema alignment with hvsim

The orbital element names mirror `src/hvsim/ephemeris/elements.py` (`Elements`)
and the `Moon`/`Station` dataclasses in `bodies.py`, so a future loader can map a
filled-in `orbit` block onto the existing Keplerian machinery with minimal
translation. Note hvsim currently assumes a single primary (heliocentric); a
**binary** system will need a two-primary extension — the `binary` block in the
system file captures the data that extension will need.

## Status

First cut — generated 2026-06-13 from the two wiki pages above. Open to schema
revision. Known follow-ups:

- Decide loader format (JSON as-is, or convert to YAML for hand-editing comfort).
- Confirm parent bodies for HMSS Vulcan / Weyland against the primary novels.
- Derive first-pass orbital elements (non-canon) so the sim can actually place
  Manticore's bodies.
- Build out referenced systems (Hancock, Basilisk, Trevor's Star, Junction
  termini destinations).
