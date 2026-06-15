---
name: expand-galaxy
description: >-
  Orchestrates a full Honorverse galaxy expansion for the hv-simulator: scrape
  new systems / ship classes with the scribe skills, run the data pipeline
  (orbit-derive -> coordinate-frame -> universe-compiler), verify the engine sees
  the new content, and append a dated entry to docs/galaxy-changelog.md. Use when
  asked to "expand the galaxy", "add a system / ship class to the dataset", or
  "scrape and compile <system>" — anything that grows data/ and must end with a
  recompiled artifact + changelog entry. Delegates canon judgment to the scribes;
  this skill is the sequencer + verifier + bookkeeper.
---

# Expand the Galaxy

A runner that turns "add <systems / ships> to the universe" into a verified,
recorded change. The hard canon-vs-fabricated judgment lives in the scribe
skills; this skill **sequences** them, runs the deterministic pipeline, proves
the engine resolves the result, and keeps `docs/galaxy-changelog.md` honest.

All commands are run from the repo root (`hv-simulator/`). The data source of
truth is `data/`; the compiled artifact is `build/universe.db` (gitignored).

> Codified from the Sprint 012 run that added Beowulf (`sigma-draconis`),
> Trevor's Star, and the Solarian Nevada-class battlecruiser. Follow these steps
> in order; each is cheap to re-run (the pipeline is deterministic).

## When to use

- "Expand the galaxy" / "add the Gregor / Hennesy / Erewhon system".
- "Add a <navy> ship class (and a few ships)".
- Resolving a stubbed wormhole terminus into a real, placed system.

Not for: schema/contract changes, engine features, or travel/routing (Phase 2b).

## Prerequisites (read once)

- Scribe skills exist under `.claude/skills/honorverse-{system,ship,wormhole}-scribe/`
  — they fetch Fandom wikitext via the MediaWiki API and own the canon flagging.
- `just` recipes: `derive-orbits`, `frame`, `compile-data`, `galaxy-summary`, `check`.
- `docs/galaxy-changelog.md` exists with a baseline entry (newest-first).

## Workflow

### 1. Snapshot the current state (for the changelog diff)

```sh
just compile-data    # ensure the artifact matches data/ before measuring
just galaxy-summary  # capture counts/lists BEFORE the expansion
```

Keep this output — the changelog entry reports deltas against it.

### 2. Scrape the new content (delegate to the scribes)

Invoke the right scribe per artifact; let it make the canon calls and write the
`data/` JSON. Per-fact `canon`/`determined` flags and CC BY-SA attribution are
the scribe's job, not this skill's.

- **System** → `honorverse-system-scribe` (writes `data/systems/<id>-system.json`).
  - Pick the system `id` to match any existing stub it resolves (e.g. the
    wormhole terminus already points at `sigma-draconis`).
  - Author `location` with a **reference + distance_ly + direction** the frame
    can resolve (`north/south/east/west` tokens; reference chains back to `sol`).
    Choose a bearing consistent with canon distances to *other* anchors when you
    can (e.g. Sigma Draconis is 40 ly from Sol and ~475 from Manticore → roughly
    on the Sol-Manticore line → `reference: sol, direction: galactic north`).
  - **Do not** hand-write `orbit` or `coordinates` blocks — the pipeline fills
    them. Bodies only need `type` (`planet` for gas giants too, with
    `subtype: gas_giant`), `orbit_index`, `habitable`, and lore.
  - Spectral type drives the hyper-limit lookup; use a class the hyperspace
    table covers (O/B/A, F0–F9, G0–G9, K0–K9, M0–M9). Fabricated → flag it.
- **Ship class** → `honorverse-ship-scribe` (appends to
  `data/ships/ship-classes.json` `classes[]`; ships to `data/ships/ships.json`).
  - Normalize European decimal commas in infobox accel (`487,7` → `487.7`).
  - Read the unlabelled accel as **max**; the `80%` figure is normal. Use
    `max_g` for the sim.
  - A new `affiliation_nation_id` is fine — the compiler stubs unbuilt nations.

> **Editing JSON by hand:** append to existing registry files with a targeted
> edit (match the last object's close + `]`), not a full rewrite — preserve the
> 2-space indent so the diff stays small.

### 3. Run the pipeline

```sh
just derive-orbits   # fabricate Keplerian orbits (canon:false) into data/
just frame           # fabricate galactic coordinates into data/ systems
just compile-data    # data/ JSON -> build/universe.db (read-only artifact)
```

Watch the output: `frame` prints each system's XYZ (new systems should appear
with sane coordinates); `compile-data` prints the row counts.

### 4. Verify the engine sees it

```sh
just galaxy-summary  # confirm built-count rose, stubs fell, classes/ships rose
```

Then prove the engine *resolves* the new content (not just that rows exist):

```sh
cd engine && uv run python - <<'PY'
from hvsim.universe import Universe, star_positions, body_positions, inter_system_distance
import datetime as dt
u = Universe.open("../build/universe.db")
t = dt.datetime(2026, 6, 15, tzinfo=dt.timezone.utc)
for sid in ("<new-system-id>",):
    print(sid, "coords:", u.system(sid).get("coord_z_ly"))
    print("  stars:", list(star_positions(u, sid, t)))
    print("  bodies:", list(body_positions(u, sid, t)))
print(inter_system_distance(u, "manticore", "<new-system-id>"))
PY
```

Expected: coordinates set, stars/bodies place with system-namespaced ids
(`<system>:<body>`), wormhole links present, `inter_system_distance` returns a
`frame` or `wormhole-canon` method. (Optionally hit the running API:
`/systems`, `/systems/{id}/bodies`, `/wormholes`.)

### 5. Append a changelog entry

Edit `docs/galaxy-changelog.md` — add a **new dated section at the top**
(newest-first), with: what was added (one bullet per system/class), stub→built
resolutions, the engine-verification facts, and **count deltas** computed from
the step-1 snapshot vs. the step-4 `galaxy-summary`. Paste the post-expansion
`galaxy-summary` block verbatim so the numbers are auditable.

### 6. Gate + commit

```sh
just check           # engine tests + lint + format, and all tools' tests
```

Commit `data/`, `build/`-adjacent code if any, and `docs/galaxy-changelog.md`
together. (`build/universe.db` itself is gitignored — it recompiles from `data/`.)

## Output checklist

- [ ] New `data/` files written by the scribe(s), canon-flagged + attributed.
- [ ] `derive-orbits` / `frame` / `compile-data` ran clean; `frame` placed the
      new system(s); `compile-data` row counts rose as expected.
- [ ] Engine verify: new systems carry coordinates, bodies place, wormhole links
      resolve, `inter_system_distance` works.
- [ ] `docs/galaxy-changelog.md` has a new dated entry with deltas + the
      `galaxy-summary` block.
- [ ] `just check` green; contract version unchanged unless a real need surfaced.

## Notes

- **Scribes own canon; this skill owns sequencing + proof + bookkeeping.** If a
  run reveals the scribe should emit something this flow needs (e.g. a
  machine-readable "what I added" summary), fold that back into the scribe — but
  only when the run actually shows the need. The Sprint 012 run did not: the
  `galaxy-summary` helper over the artifact was enough to keep the changelog
  honest.
- The pipeline is deterministic and recompilable — re-running it never loses
  hand-authored data, so iterate freely.
