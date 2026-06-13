# Honorverse Simulator (`hvsim`)

A space-travel simulator set in David Weber's *Honorverse*. The core value is
**realism of the clock**: ships take real wall-clock hours, days, and weeks to
reach their destinations, and the service reports where everything is *right
now* — evaluated analytically at the queried timestamp, with no game loop and
no drift. It is deliberately not fast or flashy.

## Status

Early development. Phase 1 (the in-system Sol ship simulator) is being built
sprint by sprint.

- Design: [`planning/004-project-plan.md`](planning/004-project-plan.md) is the
  authoritative plan. (`001`–`003` are earlier exploratory transcripts.)
- Execution: [`sprints/`](sprints/) — one short spec + task list per sprint.

## Toolchain

- Python 3.12+, managed with [`uv`](https://docs.astral.sh/uv/).
- [`ruff`](https://docs.astral.sh/ruff/) for lint/format, `pytest` for tests.

```sh
uv sync              # create the env and install dev dependencies
uv run pytest        # run the test suite
uv run ruff check .  # lint
```

## Layout

```
src/hvsim/
  ephemeris/   analytic planet/body positions (Keplerian elements)
  kinematics/  closed-form trajectory math
  flightplan/  compile flight plans into absolute-time segments
  clock/       SimClock — the only time source
  api/         FastAPI service (added in a later sprint)
tests/         pytest suite
```

## License

[MIT](LICENSE)
