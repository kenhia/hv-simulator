# hvsim — engine

The Honorverse ship-travel simulator engine (the `hvsim` Python package): pure
ephemeris/kinematics math plus the FastAPI service. Part of the
[hv-simulator](../README.md) monorepo; see the root README for the full project.

```sh
cd engine
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run where-is saturn
```
