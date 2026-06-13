# Sprint 001 — Bootstrap

## Goal

A runnable, tested, lint-clean Python project skeleton — `uv run pytest` passes
on a trivial test and `ruff` is clean, so every later sprint starts from green.

## Scope

- `git init` and a sensible `.gitignore`.
- `uv`-managed project: `pyproject.toml`, Python 3.12+, pinned dev tooling
  (`pytest`, `ruff`).
- The `src/hvsim/` package skeleton with the empty subpackages from the plan
  (`ephemeris/`, `kinematics/`, `flightplan/`, `api/`, `clock/`), each with an
  `__init__.py` so imports resolve.
- One placeholder test proving the toolchain runs.
- A top-level `README.md` pointing at `planning/` and `sprints/`.

## Out of scope

- Any real ephemeris, kinematics, or API code (that's Sprint 002+).
- FastAPI, SQLAlchemy, SQLite, Docker — not added until the sprint that needs
  them, to keep the dependency surface honest.
- CI — local green is enough for now.

## Tasks

- [x] `git init`; add `.gitignore` (Python, `.venv`, `*.db`, `__pycache__`, etc.).
      (`git init` was already done; added `.gitignore`.)
- [x] `uv init` / author `pyproject.toml` (project name `hvsim`, requires-python >=3.12).
- [x] Add dev deps: `pytest`, `ruff`. Configure `ruff` (line length, rule set) and
      `pytest` (testpaths) in `pyproject.toml`.
- [x] Create `src/hvsim/` + the five subpackages, each with `__init__.py`.
- [x] Add `tests/test_smoke.py` that imports `hvsim` and asserts a trivial truth.
- [x] Write top-level `README.md` (what the project is, link to `planning/004`
      and `sprints/`).
- [x] Commit on a branch; verify the acceptance criteria below.

## Acceptance criteria

- `uv run pytest` exits 0 with at least one passing test.
- `uv run ruff check .` reports no errors.
- `python -c "import hvsim"` succeeds inside the project env.
- `git log` shows the initial commit; working tree clean.

## Notes / decisions

- Toolchain (uv / ruff / pytest, `src/` layout) is fixed in
  `planning/004-project-plan.md`. Once this sprint lands, update `CLAUDE.md` to
  replace the "planned toolchain (not yet set up)" section with the real commands.

## Outcome — DONE

- Shipped on branch `sprint-001-bootstrap`. All acceptance criteria verified:
  `uv run pytest` (1 passed), `uv run ruff check .` clean, `import hvsim` works.
- `uv` resolved CPython **3.13.13** (satisfies `>=3.12`); kept as-is.
- Also added an MIT `LICENSE` (© 2026 Ken Hiatt) and committed `uv.lock`.
- `CLAUDE.md` toolchain section updated from "planned" to real commands.
