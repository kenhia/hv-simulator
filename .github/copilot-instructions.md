<!-- kproject:begin — managed by kprojects; do not edit inside this block -->
## kproject conventions

This project uses the kproject minimal harness
(<https://github.com/kenhia/kprojects>). Keep context small; prefer doing
over ceremony.

### Layout

- `sprints/` — the project's evolution, one record per PR-sized unit of
  work (a "sprint")
  - `planning/` — planning docs; at minimum `roadmap.md` (the general plan)
  - `review/` — more formal reviews as the project matures
  - sprint records: `###-<short-name>.md` for small projects, or a
    `###-<short-name>/` directory of files for larger/more formal ones
  - a sprint record is one informal narrative: goal, decisions, what
    shipped, follow-ups — written during the sprint, not after
- `docs/` — project documentation, architecture, usage
- `.scratch/` — git-ignored scratch space for user or agent ephemera;
  use it instead of /tmp
- `justfile` — dev recipes; default recipe is `@just --list`; `just check`
  runs the CI gates; `just deploy` (or variants) if the project deploys
- `.env` — git-ignored; tokens and environment vars

### Workflow

- One sprint ≈ one PR. Sprint proposals and work items are managed in
  `korg`; durable cross-project knowledge goes in `klams`.
- If the korg or klams MCP tools are unavailable in your session, say so
  up front — don't silently work around missing infrastructure.
- TDD preferred: write the failing test first when practical.

### Tooling preferences

- Python managed by `uv`; lint/format with `ruff`; typecheck with `ty`
  (astral toolchain)
- License is MIT unless specifically directed otherwise
<!-- kproject:end -->

## Project

An "Honorverse" (David Weber) space-travel simulator. The **core value is
realism of the clock**: ships take real wall-clock hours/days/weeks to reach
their destinations, and the system reports where everything is *right now*.
It is deliberately **not** fast or flashy — do not optimize toward
arcade-speed travel or heavy graphics.

`CLAUDE.md` carries the long-form version of this section (phase-by-phase
status, every subsystem). Same facts, more detail — keep the two in step.

### Layout

Monorepo: `engine/` (the hvsim Python package + FastAPI service, MIT),
`tools/` (standalone tools, each its own pyproject), `data/` (Honorverse
dataset, JSON source of truth — **separate CC BY-SA 3.0 license**),
`contracts/` (the versioned language-agnostic seam: universe-artifact SQL DDL
+ engine OpenAPI), `ui/` (SvelteKit + Canvas-2D galaxy app), plus `deploy/`
and `grafana/`.

### Build / run / test

- **Gate: `just check` from the repo root** — engine pytest + `ruff check` +
  `ruff format --check`, the four tools' test suites, `validate-data`, and
  `just ui-check`. Extend it; don't replace it.
- Engine commands run **in `engine/`** under `uv` (`uv sync`, `uv run pytest`,
  `uv run where-is saturn`). Python `>=3.12`.
- `just deploy` / `health` / `fleet` target the host in `.env`
  (`HVSIM_HOST`/`HVSIM_PORT`, default `kubsdb:4667`).

### Read first

- `sprints/planning/004-project-plan.md` — the authoritative design
- `sprints/planning/007-ui-vision.md` — the Phase 2.5 UI plan
- the highest-numbered `sprints/###-*.md` — what is in flight
- `contracts/` and `docs/terminology.md`

### Invariants (don't design against these)

- **No game loop and no background physics tick.** Filed plans compile to
  absolute-time `Segment` rows; `des/` replays sparse boundary events and
  evaluates the active segment analytically. Zero drift, fully cacheable.
- **`SimClock` is the only time source** — never hardcode `now()` in domain
  code. Production runs at rate 1.0; rate/jump exist for dev and tests.
- **Physics never mixes with world-building.** `ephemeris/` and `kinematics/`
  stay pure functions, testable without the service running.
- Universe data flows `data/` JSON → `just derive-orbits` + `just frame` →
  `just compile-data` → `build/universe.db` (contract v0.5.0), which the
  engine loads via `HVSIM_UNIVERSE_DB`. Never hand-edit the artifact.
- SI units (m, s) internally; convert to km/AU and human-readable durations
  only at the API boundary.
- In comments/docstrings/strings write math with the ASCII hyphen-minus `-`,
  not U+2212 (ruff RUF001/002/003 enforce this).
