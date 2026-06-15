# Sprint 012 — Expand the galaxy (pipeline integration) + changelog

Implements **Phase 2a.1**. Proves the data→artifact→engine pipeline handles real
expansion by adding real systems via the scribes — the verification *is* useful
content. Establishes a galaxy changelog, and codifies the proven flow as an
`expand-galaxy` orchestrator skill. **No travel** (that's 2b).

## Goal

Add **Beowulf (`sigma-draconis`)** and **Trevor's Star** plus **≥1 new ship
class**, run the full pipeline end-to-end, and confirm the engine sees them.
Stand up `docs/galaxy-changelog.md` (baseline first, then this expansion). Finish
by codifying the `expand-galaxy` orchestrator skill from the run we just did.

## Decisions baked in (this session)

- **Both systems** this sprint: Beowulf (the Sol→Manticore on-ramp, highest-value
  per data `001`) and Trevor's Star (San Martin; Manticore-linked). Both resolve
  currently-stubbed wormhole termini into real systems.
- **≥1 new ship class** — prefer a navy/affiliation not yet represented (a
  Solarian or Andermani class), to exercise new-nation stubbing too.
- **Changelog** (`docs/galaxy-changelog.md`): a `galaxy-summary` helper reads the
  compiled artifact so entries are accurate; **baseline established before the
  first scrape**, then an entry per expansion. Maintained going forward by the
  skill.
- **Orchestrator skill built LAST**, from the proven run (not a guessed flow).

## Scope

### 1. Baseline changelog (before scraping)
- `docs/galaxy-changelog.md` — dated, newest-first entries. **Baseline entry**
  captures the *current* galaxy from `build/universe.db`: systems (built vs
  stubbed), bodies, ship classes, ships, junctions, links, hyperspace bands.
- A small **`galaxy-summary`** helper (script + `just galaxy-summary`) that prints
  those counts/lists from the artifact, so changelog entries are generated from
  truth, not memory.

### 2. Scrape the new content (scribes; network + canon judgment)
- `honorverse-system-scribe` → Beowulf (`sigma-draconis`) and Trevor's Star
  system files (stars, bodies, places, location/bearing, canon flags). Resolves
  their stub rows.
- `honorverse-ship-scribe` → ≥1 new ship class + a few ships (new
  affiliation if possible).
- Keep the per-fact `canon`/fabricated flagging + CC BY-SA attribution.

### 3. Run the pipeline
- `just derive-orbits` → `just frame` → `just compile-data` → engine. Confirm the
  new systems place, bodies are placeable, wormhole links to Manticore are
  present, and the new class/ships compile.

### 4. Changelog entry for the expansion
- Append a dated entry (from `galaxy-summary` diff + narrative): systems added,
  class(es)/ships added, stub→built resolutions, count deltas.

### 5. `expand-galaxy` orchestrator skill (LAST)
- `.claude/skills/expand-galaxy/SKILL.md` — a runner/checklist that sequences:
  invoke the right scribe(s) → `derive-orbits` → `frame` → `compile-data` →
  verify (engine sees it) → **append a changelog entry** (via `galaxy-summary`).
  Built from this sprint's actual steps; the scribes keep the canon judgment.
- **Tweak the scribes only if the run shows a need** (e.g. to emit a
  "what I added" summary the changelog/skill consumes) — conditional, captured
  from the real run.

## Out of scope

- **Travel / DES core / routes / wormhole queues** — Phase 2b.
- The other stubbed terminus systems (Gregor, Hennesy, Matapan, Lynx, Erewhon
  spur) — later expansions, now cheap via the new skill.
- Full Solarian/Andermani fleet coverage — just enough to test (≥1 class).
- Frame precision beyond the heuristic; Sol stays special-case.

## Tasks

- [x] `galaxy-summary` helper + `just galaxy-summary`; write the **baseline**
      `docs/galaxy-changelog.md` from it (before any scrape).
- [x] Scribe → Beowulf (`sigma-draconis`) + Trevor's Star system files (resolve
      the stubs); scribe → ≥1 new ship class + ships (Solarian Nevada-class BC).
- [x] `just derive-orbits` / `frame` / `compile-data`; verify engine: both
      systems place + have coords, wormhole links present, new class/ships compile
      and appear via `/systems`, `/wormholes`, the fleet.
- [x] Append the expansion entry to `docs/galaxy-changelog.md`.
- [x] Write the `expand-galaxy` orchestrator skill from the proven flow (incl.
      the changelog step); tweak scribes iff the run showed a need.
- [x] `just check` green (engine + tools); README/CLAUDE note the changelog +
      skill.

## Acceptance criteria

- `docs/galaxy-changelog.md` exists with a **baseline** entry (pre-scrape state)
  and an **expansion** entry; both accurate to `galaxy-summary` over the artifact.
- After recompiling, **Beowulf and Trevor's Star are real systems** (no longer
  bare stubs): placed in the frame (coordinates set), bodies placeable, and their
  wormhole links to Manticore present. `/systems` count goes up; both appear with
  coordinates; `/wormholes` resolves their links.
- **≥1 new ship class + ships** compile and appear (new nation stubbed/built as
  needed; FKs hold).
- An **`expand-galaxy` skill** exists that sequences scrape → tools → verify →
  changelog, reflecting the steps actually run.
- `just check` green (engine 69+ tests + all tools); Sol unchanged; contract
  unchanged (v0.1.1) unless the run surfaces a real need.

## Notes / decisions

- **Network + canon judgment:** the scribes hit the live Honorverse wiki and make
  canon-vs-fabricated calls; this sprint involves real scraping decisions, not
  just mechanical steps. Bearings for the new systems are fabricated (`canon:false`)
  like the existing four.
- The changelog is *narrative over the data's evolution* — complementary to git
  history; the `galaxy-summary` helper keeps it honest.
- Skill-last is deliberate (Phase 2a.1): codify the flow we proved, not one we
  guessed. The scribe tweak (if any) gets folded in then.
- Expansion is the real payoff: once the skill exists, adding the remaining
  termini (Gregor, Hennesy, …) is a one-command-ish flow.

## Outcome

Done. Added **Beowulf (`sigma-draconis`)** — Solarian K0, 40 ly from Sol on the
Sol-Manticore line, worlds Beowulf + Cassandra + gas giant Enlil + the Diomedes
Belt — and **Trevor's Star** — G2, 210 ly galactic-east of Manticore, the
high-gravity world San Martin. Added the **Nevada-class** Solarian League Navy
battlecruiser (first SLN hull in the set) + three ships (SLNS *Nevada*,
*Camperdown*, *Jean Bart*).

Pipeline ran end-to-end (`derive-orbits` → `frame` → `compile-data`). Engine
verified: both systems carry frame coordinates (Sigma Draconis (0,0,40) ly,
Trevor's Star (210,0,512) ly), their stars/bodies place with system-namespaced
ids, the Manticore wormhole links resolve (475 / 210 ly), and
`inter_system_distance` returns Sol↔Sigma-Draconis = 40 ly (frame) plus the
canon wormhole spans. Built systems **4 → 6** (stubs 9 → 7), stars 5 → 7, bodies
31 → 35, belts 5 → 6, places 17 → 20, ship classes 13 → 14, ships 30 → 33.
Contract unchanged (**v0.1.1**); nations unchanged (7).

Stood up `docs/galaxy-changelog.md` (baseline + expansion entries) and the
`just galaxy-summary` helper (markdown artifact snapshot, so entries are
generated from truth). Codified the **`expand-galaxy`** orchestrator skill from
the proven run (scrape → pipeline → verify → changelog). The run did **not**
require a scribe tweak — the `galaxy-summary` helper over the artifact was enough
to keep the changelog honest. `just check` green (69 engine tests + all tools).
