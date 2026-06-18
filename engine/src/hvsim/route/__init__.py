"""route — multi-mode interstellar routes compiled onto the discrete-event core.

A filed :class:`Route` (mode-tagged legs: n-space / hyper / wormhole) compiles via
:func:`compile_route` into DES :class:`~hvsim.des.Segment`s the engine executes.
All travel parameters (hyper limits, band speeds, inter-system distances, the
wormhole buffer) are read from the universe artifact — the engine stays a
configurable physics box. Route-*finding* is Sprint 015's nav-planner; routes
here are hand-filed.
"""

from .find import plan_route, plan_route_multi
from .plan import (
    FILED_ROUTE_SCHEMA,
    CompiledRoute,
    NotAtOrigin,
    Route,
    RouteLeg,
    body_resolver,
    compile_route,
    fly_filed_route,
    from_filed,
    resolve_fleet,
    resolve_fleet_junctions,
    resolve_route,
    ship_from_artifact,
    ship_from_transponder,
    simulation_for_route,
    to_filed,
)

__all__ = [
    "FILED_ROUTE_SCHEMA",
    "CompiledRoute",
    "NotAtOrigin",
    "Route",
    "RouteLeg",
    "body_resolver",
    "compile_route",
    "fly_filed_route",
    "from_filed",
    "plan_route",
    "plan_route_multi",
    "resolve_fleet",
    "resolve_fleet_junctions",
    "resolve_route",
    "ship_from_artifact",
    "ship_from_transponder",
    "simulation_for_route",
    "to_filed",
]
