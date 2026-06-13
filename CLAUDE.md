# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is in the **planning stage** — there is no application code yet,
only design documents in `planning/`. Read `planning/004-project-plan.md` first;
it is the authoritative plan and supersedes the earlier exploratory chats
(`001`–`003`, which are saved M365 Copilot transcripts kept for context).

When you write the first code, update this file to replace the "planned" notes
below with the real commands and layout.

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

## Planned toolchain (from `planning/004-project-plan.md`, not yet set up)

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy + SQLite
- `uv` for env/deps, `ruff` for lint/format, `pytest` for tests
- Docker + docker-compose (matches the multi-container Phase 2/3 future)
- Intended package layout: `src/hvsim/` with `ephemeris/`, `kinematics/`,
  `flightplan/`, `api/`, `clock/`

SI units (m, s) internally; convert to km/AU and human-readable durations only
at the API boundary.
