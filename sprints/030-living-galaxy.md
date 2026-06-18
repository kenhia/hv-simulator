# Sprint 030 — Living galaxy (expand systems, nations, ships)

A **dedicated expansion sprint** (data, not engine): grow the dataset via the
`expand-galaxy` skill so the map has more to show, the famous nations are real
(not compiler stubs), and the registry has more ships. First, teach the skills to
place new systems *naturally* so the batch lands well.

Plan: demo-first roadmap (`planning/007`) · KWIs #79 (skill update) + #66 (nations).
Driven by the `expand-galaxy` orchestrator → scribes → pipeline → verify → changelog.

> **Demo tomorrow (2026-06-19).** Keep this batch tight and solid; the scope below
> is confirmed. We may expand *after* seeing it live — leave the pipeline ready to
> add more nations/systems quickly, but don't over-reach today.

### Confirmed scope (2026-06-18)

- **Systems:** Republic of Haven (Nouveau Paris), **Gregor** (Manticore Junction
  terminus), **Erewhon** (hosts `erewhon-junction`).
- **Nations:** Republic of Haven, Protectorate of Grayson, Republic of Beowulf,
  Solarian League (covers every built system's affiliation).
- **Ships:** a few per new nation (1-2 classes + several hulls each) so the board
  shows new factions — Haven for sure, Grayson if it falls out naturally.

## Goal

A noticeably fuller, more believable galaxy: the **Republic of Haven** exists
(system + nation), the systems we already show have **real nation records** instead
of stubs, a couple of **junction-terminus stubs are resolved** into placed systems,
and the **ship registry grows** with non-Manticoran navies. All authored through the
skills (canon judgment stays there); this sprint sequences + verifies + records.

## Part A — Teach the skills natural placement (#79) — do first

Update the frame tool + `expand-galaxy` skill + `honorverse-system-scribe` so new
systems land naturally (off the rigid 90° cardinals) without looking like a *new*
repeated pattern. Per Ken's #79 note: a deflection should be **varied within the
arc, always ≥3° off the cardinal, and never a constantly-repeated angle** (a fixed
repeated offset looks as unnatural as all-90°).

**Reconciling "random" with reproducible coords.** `just frame` regenerates coords
from `data/` every run, so they must be **stable** (no churn / wandering systems).
Pure per-run randomness breaks that. Resolution = **random once, then frozen**:

1. **Floor the deflection at 3°:** the bearing-arc magnitude is constrained to
   **[3°, 22.5°]** either side of the cardinal (today it spans [−22.5°, +22.5°],
   which can land a system ~on the axis — e.g. Trevor's auto −0.97°, why it needed a
   manual nudge). Fix `_jitter_rad` in `tools/coordinate-frame` to map to
   |angle| ∈ [3°, 22.5°] with a hash-derived sign; floors *all* systems off-axis.
2. **Varied, not repeated:** the per-system angle stays spread across the arc (hash
   of the id → effectively uniform; collisions negligible) — no constant offset.
3. **Random-at-incorporation, frozen:** when the scribe authors a *new* system it
   assigns a deflection (a fresh varied pick within [3°, 22.5°]) and **stores it in
   `location`** (an explicit `bearing_deg`-style field), so it's chosen per-system at
   incorporation yet reproducible thereafter. The floored hash is the fallback.
4. **Hand-tune + eyeball:** `location.bearing_nudge_deg` (canon:false, +CCW,
   additive) for the rare "two landed too close"; the orchestrator runs `just frame`
   and **eyeballs the spread** (no collinear stacks, nothing on-axis) before
   compiling.

Also: prefer a **specific canon bearing** (intercardinal / a terminus direction)
over a bare cardinal when canon supports it — the more specific, the less we
fabricate. Point the skills at one source-of-truth note (the frame tool docstring).

## Part B — Nations for linked systems (#66)

Author the nations our built/new systems affiliate to, so transponder nation
codes + any nation-facing UI read against real records, not stubs. At minimum:

- **Republic of Haven** (capital: Haven / Nouveau Paris) — the headline gap.
- **Protectorate of Grayson** (Yeltsin's Star, already a built system).
- **Republic of Beowulf** (Sigma Draconis, already built).
- **Solarian League** (Sol, Sigma Draconis affiliation).
- Any others referenced by termini/affiliations as we go (Erewhon, Silesia, …).

If a `honorverse-nation-scribe` doesn't exist, either add a thin one or have the
system-scribe pull the star nation alongside the system (per #66).

## Part C — Systems (resolve stubs + the headline addition)

Build out, via `honorverse-system-scribe` (each resolves an existing stub id where
one exists, so wormhole termini connect up):

- **Haven** (Republic of Haven capital) — the marquee system.
- **Gregor** — a Manticore Junction terminus (resolving it makes the junction graph
  and the 029 terminus markers richer).
- **Erewhon** — hosts the *other* junction (`erewhon-junction`); resolving it makes
  the second junction real on the map.

(Final list confirmed with the user before scraping — see the scope question.)

## Part D — Ships (grow the registry)

Add a few non-Manticoran navy **classes + ships** via `honorverse-ship-scribe` so
the fleet board / faction colours show more nations:

- **People's Navy / Republic of Haven Navy** classes (e.g. a waller + a cruiser).
- Optionally **Grayson Space Navy**.
- Enough hulls that each new nation shows several ships on the board.

## Process (the expand-galaxy workflow)

1. `just compile-data && just galaxy-summary` — snapshot BEFORE (for the delta).
2. Scribes author `data/` JSON (systems, nations, ship classes + ships).
3. Pipeline: `just derive-orbits` → `just frame` (eyeball spread, Part A) →
   `just compile-data`.
4. Verify the engine resolves it: `where-is` a new body, `GET /systems`,
   `/wormholes`, `/junctions`; transponder uniqueness holds.
5. `just galaxy-summary` AFTER; append a dated `docs/galaxy-changelog.md` entry
   (built-vs-stubbed, counts) generated from truth.
6. `just check` green; `just contracts` (no schema change expected).

## Tasks

- [ ] Part A: update `expand-galaxy` + `honorverse-system-scribe` (placement model
      + eyeball step); commit the skill changes.
- [ ] Part B: author the linked nations (Haven, Grayson, Beowulf, Solarian League).
- [ ] Part C: scrape + place the confirmed systems (Haven + junction termini).
- [ ] Part D: add the new navy ship classes + ships.
- [ ] Run the pipeline; eyeball the galaxy spread; verify engine resolution.
- [ ] `docs/galaxy-changelog.md` entry (before/after deltas).
- [ ] `just check` + `just contracts` green; UI sanity (new systems placed, nations
      colour ships, junction termini click through).

## Acceptance criteria

- The Republic of Haven is a placed system with a real nation record; its ships
  show on the board with a distinct faction colour.
- The previously-stubbed nations behind our built systems are authored (no longer
  bare compiler stubs).
- At least the confirmed junction-terminus systems are placed and connect on the
  map (029 terminus markers click through to their junction).
- New systems land naturally (no collinear stack); coordinates reproducible.
- Galaxy-summary counts grow; changelog entry recorded; all gates green.

## Out of scope (deferred)

- Engine/travel changes (#76 run-to-nexus, #77 distinct termini) — separate sprints.
- Repeating routes (#59) — Sprint 031.
- Exhaustively building *every* stub — this is a curated, demo-weighted batch.
