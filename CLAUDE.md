# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early development, executed sprint by sprint. Done so far: project skeleton
(Sprint 001) and the `ephemeris` module (Sprint 002 — analytic planet positions
+ a `where-is` CLI). The `kinematics`, `flightplan`, and `api` subpackages are
still stubs filled in by later sprints.

- `planning/004-project-plan.md` is the authoritative design; read it first.
  (`001`–`003` are earlier M365 Copilot transcripts kept for context.)
- `sprints/` holds one short spec + task list per sprint. Check the highest-
  numbered file for what's in flight; a sprint is done only when every
  acceptance criterion in it is verified.

## What this project is

An "Honorverse" (David Weber) space-travel simulator. The **core value is
realism of the clock**: ships take real wall-clock hours/days/weeks to reach
their destinations, and the system reports where everything is *right now*.
It is deliberately **not** fast or flashy — do not optimize toward arcade-speed
travel or heavy graphics.

## Architecture intent (read before designing anything)

The system is decomposed so that the physics never mixes with world-building.
This separation is load-bearing — preserve it:

- **Ship simulator microservice (Phase 1, the current focus)** stays *dumb,
  deterministic, and math-driven*. It never invents lore, never computes routes.
  It compiles a filed flight plan into absolute-time `Segment` rows (each a
  closed-form piece of trajectory) and answers "where is everything at time T"
  analytically. **There is no game loop and no background physics tick** —
  state queries evaluate kinematics at the current timestamp. This gives zero
  drift and full cacheability; do not introduce a simulation loop.
- **`SimClock`** (epoch offset + rate multiplier) is the only time source.
  Production runs at rate 1.0 — that real-time pacing is the whole point.
  The rate/jump controls exist for dev and tests so a multi-hour trip can be
  fast-forwarded; never hardcode `now()` in domain code, go through the clock.
- **Universe builder, hyperspace/wormholes (Phase 2)** and **combat + LLM
  narrative + admiral agents (Phase 3)** are separate services added later.
  The ship simulator gains only new *segment kinds* (e.g. `hyper_cruise`,
  `wormhole_transit`); route planning and worldgen live outside it.

### Physics facts that constrain the math (verified in `004`)

- Newtonian kinematics with a velocity cap (0.6c). Reaching 0.6c at 250 g needs
  ~44 AU of runway, so the cap rarely engages in-system; relativity is a 2–6%
  effect and is only *reported* (`subjective_time_delta`), not simulated.
- In-system Sol trips are **brachistochrone** (accel, flip at midpoint, decel) —
  Earth→Saturn ≈ 12.7 h peaking at ~0.187c. The solver must handle both the
  brachistochrone case and accel/coast/decel, plus a moving-target intercept
  (the destination planet moves during the trip; solve by fixed-point iteration).
- Planet positions come from analytic JPL approximate Keplerian elements
  (J2000) — deterministic and offline, no external API calls.

Keep `ephemeris` and `kinematics` as **pure functions** so they are testable
without running the service.

## Toolchain & commands

Managed with `uv`. Python `>=3.12` (currently resolves to 3.13; either is fine).

```sh
uv sync                  # create .venv and install dev dependencies
uv run pytest            # run the full test suite
uv run pytest tests/test_smoke.py::test_package_imports   # run a single test
uv run ruff check .      # lint
uv run ruff format .     # format (use --check in CI / pre-ship)
uv run where-is saturn   # CLI: heliocentric position of a body (--at <iso8601>)
```

The validation gate before shipping a sprint is: `uv run pytest`,
`uv run ruff check .`, `uv run ruff format --check .` — all clean.

Package layout under `src/hvsim/`: `ephemeris/`, `kinematics/`, `flightplan/`,
`clock/`, `api/`. Kinematics and ephemeris stay **pure functions** — unit-
testable without the service running.

FastAPI, Pydantic v2, SQLAlchemy + SQLite, and Docker are in the plan but not
added until the sprint that needs them, to keep the dependency surface honest.

SI units (m, s) internally; convert to km/AU and human-readable durations only
at the API boundary.
