# Sprint 041 — finish the linked-nations data

A drawdown slice: korg proposal **#4472**, one leg of program **#4368** (the
November backlog drawdown). It covers one work item, **#66**: "expand nations
data to cover systems' linked nations (+ scribe both)". The leg ran on kai as
karc leg `hv-simulator-29c6bd`.

## Premise check

| Claim (WI 66 / proposal) | Verdict |
|---|---|
| Masada, Silesia and `star-empire-of-manticore` are still compiler stubs | **holds** — the compiled artifact had exactly these three rows with `name = id` and no government |
| The Anderman Empire is still a stub | **gone** — `andermani-empire.json` has been a real record since sprint 030. The work item's text was out of date; the proposal summary had it right. |
| The scribe does not pull in a system's nation | **holds** — `honorverse-system-scribe` excluded nation files ("Not for: building nation files from scratch"), and `expand-galaxy` said "the compiler stubs unbuilt nations" |

Only one built system pointed at a stub: **Endicott → `masada`**. Silesia was
referenced only by the Starhauler class and its one ship. The Star Empire was
referenced only by the Star Kingdom's `succeeded_by`.

## What shipped

### Three nation records (`data/nations/`)

All three are sourced from their Honorverse Wiki pages (fetched with the
scribe's own `fetch_wikitext.py`) and the canon tags those pages cite. They
mirror the sprint-030 records (`andermani-empire.json`, `republic-of-erewhon.json`).

- **`masada.json`** — Masada, Theocracy, capital world Masada in Endicott
  (HH2). Chief Elder / Council of Elders, Navy of Masada, population of about
  4.5 billion (1903 PD). Manticoran occupation since 1903 (HH3, HH5).
- **`silesia.json`** — the Silesian Confederacy, a Confederation of around 60
  systems in 9 sectors, partitioned in 1921 PD between the Andermani Empire and
  the Star Kingdom of Manticore (HH12, Companion). Its capital is the Silesia
  System (HH0, *Jayne's Intelligence Review* v1).
- **`star-empire-of-manticore.json`** — the Star Empire of Manticore, a
  Constitutional Monarchy founded 1921 PD from the Star Kingdom plus the
  Talbott Quadrant. Capital Landing on Manticore. Imperial Parliament (SI1,
  SI2, SI3, Companion).

All three ids already had transponder codes (489, 555, 419), assigned in
sprint 017, so no code moved.

### The scribe pulls a system's nation in with it

- **`honorverse-system-scribe`**: step 5 now says to author the system's
  linked nation in the same pass when `nations/<id>.json` is missing. It gives
  the field list to mirror, the no-invention rule, and the transponder code.
  The "Not for" line and the output checklist changed to match.
- **`expand-galaxy`**: the system bullet says the nation comes in with the
  system. The ship-class bullet now says that only a *system's* nation must be
  authored; ship and class affiliations may still be stubbed.

### The tests

- **`tools/validate-data.py`** (part of `just check`) fails when a built
  system's `star_nation_id` has no `nations/` record, and names the scribe step
  that fixes it. It also fails when a nation record has no transponder code.
  Both directions were exercised: real data passes, and a copy with
  `masada.json` removed fails with
  `system endicott-system.json names nation 'masada' but nations/masada.json does not exist`.
- **`tools/universe-compiler/test_compile.py`**: the new test
  `test_built_systems_point_at_authored_nations` compiles the real dataset and
  asserts that no built system joins to a stub nation, and that the three
  former stubs carry their canon names. It was written first and failed on
  Endicott → `masada` before the records existed.

## Decisions

- **Nothing invented.** A blank infobox field stays `null`: Masada's capital
  city, Silesia's capital planet and population, and the Star Empire's
  language. I had drafted "Standard English" for the Star Empire from the Star
  Kingdom's record and removed it, because the Star Empire's own page does not
  say so. A fact the flat fields cannot hold goes in `lore` as sourced prose:
  Masada's "14th century PD" founding, and Silesia's partition between two
  successors, which a single `succeeded_by` cannot express.
- **Silesia's capital is `silesia`**, the canon Silesia System. The compiler
  now stubs one more coordless system, as it already does for `hennesy` and
  `matapan`. It does not appear on the galaxy map, which renders only placed
  systems.
- **Built Manticoran systems stay affiliated to the Star Kingdom.** Re-pointing
  them to the Star Empire is an era decision, not part of authoring the record.
- **The gate covers systems only, as the brief asks.** Ship and class
  affiliations may still name an unbuilt nation. Making the ship scribe author
  nations too would be a change to its workflow, and that is not this sprint's
  call.

## Repaired in passing

- **`data/ATTRIBUTION.md` was missing 17 cited wiki pages.** Every page in the
  sprint-015/030 nation and system records' own `wiki_pages` was absent from
  the CC BY-SA source table: the six nation pages, plus New Berlin, Durandel,
  Erewhon, Gregor, Haven, Sigma Draconis and Trevor's Star. I backfilled the
  rows from each record's `wiki_pages` and `retrieved` fields, and added rows
  for the three pages read this sprint. **The overseer ruled that this belongs
  in the gate, not in a note** (CC BY-SA requires it, and the records already
  carry the fields), so `validate-data` now checks it. Every `wiki_page` and
  `wiki_pages` value at any depth in any `data/` JSON must appear in the
  `ATTRIBUTION.md` table, and a missing one fails naming the file and page.
  - Its first run found an 18th gap, `Nevada_class` in `ship-classes.json`
    (sprint 012), and I added that row.
  - It matches the table's URL column exactly, not by substring; a substring
    test would let `.../wiki/Haven` hide behind `.../wiki/Haven_System`.
  - Shown both ways: removing the Solarian League row fails, removing the
    Haven row fails (the prefix case), and the real data passes.
  - The system scribe's step 5 now says the gate enforces it.
- **`transponder-codes.json` `_doc`** still said Beowulf was "not yet a nation
  record — see kwi #66". Beowulf has had a record since 030, so the stale
  clause is gone. No code changed; the gate still reads `data OK`.
- **The universe-compiler `_stub_missing_refs` docstring** used
  `protectorate-of-grayson` as its example of a stubbed nation, which has not
  been true since 030. The example now names `hennesy` and `silesia`.

## Verified

- `just compile-data` → `just galaxy-summary`: 11 nations, none stubbed;
  12 built systems, unchanged; 6 stubbed systems (`silesia` is new).
- `just check`: all green — engine 185 passed, ruff clean, compiler 5,
  orbit-derive 3, coordinate-frame 5, nav-planner 6, `data OK`, UI 68 tests.

## Follow-ups

None filed. This was an overseen leg, so findings go to the overseer in the
wrap-up handoff on korg #4472.

## Deployed

2026-11-10 04:46 UTC (2026-11-09 20:46 PST). The ship merged PR #47 as squash
commit `734b851`; the leg then ran `just deploy` from that merged `main` on kai.
The overseer cleared it explicitly; the repo has no `.sprint-deploy`.

- `just deploy` pushed and pulled `kubsdb.encke-wahoo.ts.net:5000/hvsim:734b85138677`
  and recreated the `hvsim` container. `remote-up.sh` asserted revision
  `734b85138677000d7a9b7116552119df601e351b`. Health `{"status":"ok"}`; the
  clock runs at rate 1.0 with dev controls off.
- The new artifact is live. `GET /systems` returns 18 systems (it was 17),
  including the new coordless `silesia` placeholder; Endicott's
  `star_nation_id` is `masada`.
- The UI answers. From kai, `https://kubsdb.encke-wahoo.ts.net:4667/ui/` and `/`
  both return 200. From kubsdb, the address kwebi probes
  (`http://192.168.1.60:4667`) returns 200 for both.
- kwebi (on kubsdb, `127.0.0.1:5680`) shows both Honorverse tiles,
  "Honorverse Simulator" and "hv-sim Sol", as `health.state: "up"`, status
  200, checked at 04:46:52Z, after the restart.
- Rollback target: the previous `:latest` image, via `just image-tags` /
  `just rollback <tag>`.
