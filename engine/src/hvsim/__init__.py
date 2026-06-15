"""hvsim — Honorverse ship-travel simulator.

The core value is realism of the clock: ships take real wall-clock time to reach
their destinations, and the service reports where everything is *right now*,
evaluated analytically at the queried timestamp (no game loop). See
``planning/004-project-plan.md`` for the authoritative design.
"""

__version__ = "0.1.0"
