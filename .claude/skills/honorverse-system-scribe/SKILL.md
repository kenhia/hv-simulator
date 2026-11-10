---
name: honorverse-system-scribe
description: >-
  Builds schema-conformant Honorverse star-system data files for the
  hv-simulator dataset from wiki and book sources. Use when adding or updating a
  star system in the Honorverse-Data collection — e.g. "add the Basilisk
  system", "scrape Grayson / Yeltsin's Star", "build a system file for Hancock".
  Covers fetching Fandom wikitext via the MediaWiki API (bypassing the 403),
  mapping stars/planets/moons/belts/stations into the star-system schema,
  applying the per-fact canon-vs-invented flagging convention, and updating
  nation cross-references and CC BY-SA attribution.
---

# Honorverse System Scribe

Turn an Honorverse source (primary: the David Weber novels; secondary: the
[Honorverse Wiki](https://honorverse.fandom.com), CC BY-SA 3.0) into a
schema-conformant **star system data file** for the `hv-simulator` dataset.

All paths below are relative to the **dataset root** — the directory that
contains `systems/`, `nations/`, `schema/`, `README.md`, and `ATTRIBUTION.md`.
This skill lives at `.claude/skills/honorverse-system-scribe/` inside that root.

## When to use

- Adding a new star system (`add the Basilisk system`, `scrape Yeltsin's Star`).
- Updating/correcting an existing system file with new canon.
- Filling in invented (non-canon) orbital values for an existing system.

Not for: non-astrographic lore, or a nation with no system being added (that is
a standalone data pass). The body chart is the focus — but a new system's
**linked nation is in scope** (step 5): system and nation come in together, so a
system never points at a compiler stub.

## Ground truth to read first

Before writing anything, read these so you match the established shape exactly:

1. `schema/star-system.schema.json` — the contract. The output must conform.
2. `systems/manticore-system.json` — the **gold reference**. Mirror its
   structure, field names, and level of detail.
3. `README.md` — units, the two-layer (system vs nation) model, hvsim alignment.
4. `ATTRIBUTION.md` — the source-tag legend (`HH<n>`, `Companion`, `UHH`, etc.).

## Workflow

### 1. Fetch the source wikitext

Fandom returns HTTP 403 to generic fetchers, so go through the MediaWiki API.
Use the bundled helper (stdlib-only, works on Windows and Linux):

```sh
python .claude/skills/honorverse-system-scribe/scripts/fetch_wikitext.py "Basilisk System"
```

Add `--save _raw/basilisk-system.wiki` to keep the raw source for provenance
(optional but nice for the CC BY-SA "indicate changes" requirement; `_raw/` is
gitignored-by-convention scratch).

**Pull the dedicated `<Name> System` page** — it holds the body chart (the
`=== Star Geography ===` section with the `Manticore-A I … VII` ordering). If the
user names a *planet* or a *nation* page, also fetch its system page. Cross-check
the planet's own page for gravity / day-length / population when you have it.

If the API helper is unavailable, the raw call is:
`curl -s -A "<browser UA>" "https://honorverse.fandom.com/api.php?action=parse&page=<TITLE>&prop=wikitext&format=json&formatversion=2"`
then read `.parse.wikitext`.

### 2. Map the wikitext into the schema

- **Stars**: spectral type + mass are usually canon. For a binary, capture the
  barycentric distances, eccentricity, and periastron/apastron separations in a
  `binary` block (light-minutes, suffix `_lmin`).
- **Bodies**: one entry per planet, in canon order, with `designation`
  (e.g. `Basilisk-A III`), `parent_star`, `orbit_index`, `type`, `subtype`
  (`terrestrial` / `gas_giant`), `habitable`, and named `moons`.
- **Belts**: separate `belts[]` array; note which body they follow.
- **Places**: stations, shipyards, the wormhole junction (with `termini`),
  fortifications — anything "visitable." Use `rides_on` for the body a station
  is fixed to (matches hvsim's `Station(parent=...)`).
- **Lore**: a `lore` block with `summary`, naming convention, and a sourced
  `timeline[]`. Keep flavor, but attribute it.

### 3. Apply the canon convention (the whole point)

`canon` is tracked **per fact, not per object**:

- An object is `canon: true` if its *existence/identity* is established in canon.
- Its **orbit/position is almost always `canon: false`** — the books rarely give
  semi-major axes, eccentricities, or coordinates. Use the nested block:

```jsonc
"orbit": { "canon": false, "determined": false,
           "a_au": null, "e": null, "i_deg": null, "L_deg": null,
           "long_peri_deg": null, "long_node_deg": null, "period_days": null,
           "notes": "Only order is canon; placement to be derived/invented." }
```

When you later invent or derive a value: fill it, keep `canon: false`, and set
`determined: true`. Field names mirror `src/hvsim/ephemeris/elements.py` so a
loader maps them straight onto the Keplerian machinery.

Anything you create that isn't in a source — a coordinate convention, a
separation, a station's parent body you inferred — gets `canon: false` and a
`notes` explaining the basis.

### 4. Cite sources

Every object gets a `source` (or system-level `sources`) using the tags in
`ATTRIBUTION.md`. Transcribe the wiki's citation templates (`{{HH|2}}` → `HH2`,
`{{Comp}}` → `Companion`). Flag any tag you couldn't verify against a primary
novel.

### 5. Write the files and wire up references

- Write `systems/<id>-system.json` (`<id>` = lowercase-hyphen, e.g. `basilisk`).
- **`location` block** — `reference` (chains back to `sol`) + `distance_ly` +
  `direction` (compass tokens: `north/south/east/west`, e.g. `galactic north-east`;
  prefer a *specific* canon bearing over a bare cardinal). The
  `coordinate-frame` tool fabricates absolute XYZ from this (`canon: false`); **do
  not** hand-write a `coordinates` block. Add a **`bearing_offset_deg`**: the
  system's deflection from the cardinal, **+CCW**, picked **varied within ±[3°,
  22.5°]** (never ~0° = on-axis, never a repeated constant — both look unnatural).
  Choose a fresh non-round value per system (`+7.4`, `-16.2`, …); it freezes in
  data for reproducible coords. (`bearing_nudge_deg` adds a later hand-tune.)
- **Pull in the linked nation.** Set `star_nation_id` to the owning nation's id.
  If `nations/<id>.json` does not exist yet, **author it now, in this pass**:
  - Fetch the nation's own page with the same helper (`fetch_wikitext.py
    "Silesian Confederacy"`); the system page's prose usually links it.
  - Mirror `nations/andermani-empire.json` / `nations/masada.json` exactly:
    `schema_version`, `kind: "star_nation"`, `id`, `name` (the canon name — the
    id may be shorter, e.g. `silesia`), `government`, `capital_system_id`,
    `capital_planet`, `capital_city`, `founded_pd` (an integer year, else
    `null`), `succeeded_by`, `canon`, `source`, `wiki_pages`, `retrieved`, a
    `lore` block (summary, head of state/government, military — only what the
    page states), and `territory.member_systems` listing this system by
    `system_id` with its own `canon` + `source`.
  - **Nothing invented.** An infobox field that is blank stays `null` or is
    left out — do not carry a fact over from a sibling nation. A fact the
    record's flat fields can't hold (a partition between two nations, a
    century rather than a year) goes in `lore` as prose with its source.
  - Give it a transponder code in `transponder-codes.json` if it lacks one
    (random-ish in `[42, 999]`, unused; never renumber an existing code).
  - `just validate-data` fails on a built system whose nation has no record —
    that is the check this step satisfies.
- If the nation already exists, add/confirm the system's reference in the
  relevant `nations/*.json` (member system, terminus, naval station, or
  protectorate) by `system_id`. A station in an uninhabited system (e.g. Hancock
  Station) is referenced from the nation file and also becomes a `place` in its
  own system file.
- Append the source page(s) to the table in `ATTRIBUTION.md` with the retrieval
  date.

### 6. Validate before finishing

```sh
python -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" systems/<id>-system.json
```

Then sanity-check: body count matches the chart, planets are in order per
parent star, habitable worlds flagged, every object has a `canon` flag and a
`source`. If `jsonschema` is installed, validate against
`schema/star-system.schema.json`.

## Output checklist

- [ ] `systems/<id>-system.json` conforms to the schema and parses.
- [ ] Every star/body/belt/place has `canon` + `source`.
- [ ] Orbits/positions are `canon: false` unless a source gives hard numbers.
- [ ] Linked nation exists as `nations/<id>.json` (authored now if it was a stub)
      with a transponder code; `just validate-data` passes.
- [ ] Nation cross-references updated by `system_id`.
- [ ] `ATTRIBUTION.md` source table updated with page + date.
- [ ] Lore/flavor captured and attributed.
