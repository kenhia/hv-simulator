"""route — multi-mode interstellar routes compiled onto the discrete-event core.

A filed :class:`Route` (mode-tagged legs: n-space / hyper / wormhole) compiles via
:func:`compile_route` into DES :class:`~hvsim.des.Segment`s the engine executes.
All travel parameters (hyper limits, band speeds, inter-system distances, the
wormhole buffer) are read from the universe artifact — the engine stays a
configurable physics box. Route-*finding* is Sprint 015's nav-planner; routes
here are hand-filed.
"""

from .plan import (
    CompiledRoute,
    Route,
    RouteLeg,
    body_resolver,
    compile_route,
    ship_from_artifact,
    simulation_for_route,
)

__all__ = [
    "CompiledRoute",
    "Route",
    "RouteLeg",
    "body_resolver",
    "compile_route",
    "ship_from_artifact",
    "simulation_for_route",
]
