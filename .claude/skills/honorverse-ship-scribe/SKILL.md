---
name: honorverse-ship-scribe
description: >-
  Discovers Honorverse warship classes and builds the ship-class + ship
  registries for the hv-simulator dataset. Use when adding ships or ship classes
  — e.g. "add the Andermani battlecruisers", "capture the Nike and Invictus
  classes", "add some Solarian wall classes", "register HMS Unconquered". Covers
  category-based discovery via the MediaWiki API, parsing the {{Ship}} infobox
  (mass, dimensions, acceleration, armament), the canon acceleration-label rules
  (normal vs max vs single-value), the canon-vs-derived flagging convention, and
  appending to ships/ship-classes.json and ships/ships.json with attribution.
---

# Honorverse Ship Scribe

Build and extend the two ship registries for the `hv-simulator` dataset from the
Honorverse Wiki's `{{Ship}}` infoboxes (primary source still the David Weber
novels; wiki is CC BY-SA 3.0 — see `ATTRIBUTION.md`).

The headline goal is **correct canon accelerations** for correctly-named ships,
plus armament and physical specs for flavor and future naval combat.

All paths are relative to the **dataset root** (the directory holding `ships/`,
`systems/`, `schema/`, `ATTRIBUTION.md`). This skill lives at
`.claude/skills/honorverse-ship-scribe/`.

## Ground truth to read first

1. `schema/ship-class.schema.json` and `schema/ship.schema.json` — the contracts.
2. `ships/ship-classes.json` — the **gold reference**; mirror its shape exactly.
3. `ships/ships.json` — the ship registry (each ship FKs a class by `class_id`).
4. `ATTRIBUTION.md` — source-tag legend (`HH<n>`, `Companion`, etc.).

## Workflow

### 1. Discover what exists

The wiki browses poorly; its **categories** are the reliable index.

```sh
python .claude/skills/honorverse-ship-scribe/scripts/list_category.py "Manticoran Ship Classes"
```

Known class categories: `Manticoran Ship Classes`, `Grayson Ship Classes`,
`Havenite Ship Classes` (note: "Havenite", not "Haven"), `Andermani Ship
Classes`, `Solarian Ship Classes`, plus per-type categories like
`Battlecruiser (P) Ship Classes`. For individual ships, a class page's "Known
vessels"/"Known ships" section is the index.

### 2. Fetch the infobox

```sh
python .claude/skills/honorverse-ship-scribe/scripts/fetch_wikitext.py "Reliant class"
```

The data lives in the `{{Ship}}` template at the top: `type`, `affiliation`,
`date introduced`, `preceded by` / `succeeded by`, `mass`, `length`, `beam`,
`draught`, `acceleration`, `crew`, `power`, `electronics`, `armament`,
`magazines`, `auxiliary craft`.

**Classes without their own infobox** (e.g. the GSN *Honor Harrington* class is
the RMN *Medusa*-class design under another name): pull specs from the
referenced design page, set each block's `source` to that page, and say so in
the block `notes`.

### 3. Acceleration — read the LABELS, not the position (the tricky bit)

Canon gives a sustained ("80%"/normal) figure and an emergency (max, zero-margin)
figure, but infoboxes order and label them inconsistently. Rules:

- **Paren says "maximum"/"max"** → the primary value is `normal_g`, the paren is
  `max_g`. e.g. `542.8 G (678.4 G maximum)` → normal 542.8, max 678.4.
- **Secondary says "80% accel"** → the primary (often unlabeled, sometimes with a
  kps² value) is `max_g`, the "80%" one is `normal_g`. e.g.
  `674.3 G (6.613 kps²) / 539.4 G ... 80% accel` → max 674.3, normal 539.4.
- **Single unlabeled value** → treat it as `max_g` (the capability ceiling) and
  derive `normal_g = 0.8 × max_g`, listing `"normal_g"` in that block's
  `derived`. Reading the bare value as max avoids inventing an acceleration
  *higher* than any canon figure. Sanity-check against the class's
  predecessor/successor accel (a newer ship is usually faster).
- `kps²` (km/s²) values are just unit duplicates: 1 G = 0.00980665 kps². Store G;
  ignore kps².
- The normal:max ratio is **not constant** — 80% is common on pod-era ships, but
  e.g. Reliant is ~95%. Never assume 80% when both canon figures are given.
- **The sim's `max_accel_g` should take `max_g`** (fall back to `normal_g`).

### 4. Armament

Capture a verbatim `summary`, plus a structured `by_arc` breakdown
(`broadside` / `fore` / `chase` / `aft`) keyed by weapon code when the infobox
uses the compact form. Add an `inventory` array for itemized mount lists.
Weapon-code legend (also stored at the top of `ship-classes.json`):

| Code | Meaning |
|---|---|
| M | Missile launcher / tube |
| MP | Missile-pod mount (pod-layer aft rail) — interpretation uncertain |
| L | Laser mount |
| G | Graser mount |
| CM | Countermissile launcher / tube |
| PD | Point-defense laser cluster |

### 5. Canon vs derived

Object- and block-level `canon` as elsewhere, **plus** a `derived` array on each
tech block naming the specific numeric fields we fabricated/inferred (e.g.
`"derived": ["normal_g"]`). A block can be `canon: true` while one field inside
it is derived. Where a value is simply absent in canon and we leave it null,
still flag it (`"canon": false`, list the field in `derived`) so it's clearly a
fabrication slot.

### 6. Map IDs and references

- Class `id`: lowercase-hyphen, no "class" suffix (`edward-saganami`, `sultan`).
- Ship `id`: prefix + name + hull (`hms-fearless-ca-286`, `pns-saladin`).
- `affiliation_nation_id` FKs a nation: `star-kingdom-of-manticore`,
  `protectorate-of-grayson`, `republic-of-haven` (the People's Republic during
  the wars — note the era in `notes` if relevant), etc.
- Every ship's `class_id` MUST resolve to a class in `ship-classes.json`.
- Watch for cross-links worth recording in `lore`/`notes`: ships tie to systems
  (HMS Fearless ↔ Yeltsin's Star; PNS Saladin/MNS Thunder of God ↔ Masada;
  Invictus hulls ↔ Grendelsbane Station). Use `renamed_to` for re-flagged hulls.

### 7. Append, attribute, validate

- **Append** to `ships/ship-classes.json` (`classes[]`) and `ships/ships.json`
  (`ships[]`) — don't overwrite existing entries.
- Add each class page to the `ATTRIBUTION.md` source table with the date.
- Validate: every file parses, and every `class_id` resolves. Quick check:

```sh
python - <<'PY'
import json
cl={c['id'] for c in json.load(open("ships/ship-classes.json"))['classes']}
sh=json.load(open("ships/ships.json"))['ships']
orphans=[s['id'] for s in sh if s['class_id'] not in cl]
print("classes:",len(cl),"ships:",len(sh),"orphans:",orphans or "none")
PY
```

## Output checklist

- [ ] Each class has dimensions + acceleration with correct normal_g/max_g.
- [ ] Single-value or absent fields flagged via `derived` (and canon:false).
- [ ] 1–3 ships per class, each with a resolving `class_id` and a `source`.
- [ ] Cross-links to systems/nations captured where they exist.
- [ ] `ATTRIBUTION.md` updated; both registries parse; no orphan ships.
