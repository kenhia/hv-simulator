"""route — multi-mode interstellar routes compiled onto the discrete-event core.

A filed :class:`Route` (mode-tagged legs: n-space / hyper / wormhole) compiles via
:func:`compile_route` into DES :class:`~hvsim.des.Segment`s the engine executes.
All travel parameters (hyper limits, band speeds, inter-system distances, the
wormhole buffer) are read from the universe artifact — the engine stays a
configurable physics box. Route-*finding* lives in :mod:`~hvsim.route.find` over
the precomputed :mod:`~hvsim.route.graph` topology; :mod:`~hvsim.route.repeat`
turns a round trip into an itinerary a ship lives on. :func:`compiled_at` is the
one entry point that takes any filed document and says what it is flying now.
"""

from .find import plan_route, plan_route_multi, speed_class
from .graph import RouteGraph, route_graph
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
from .repeat import (
    REPEATING_ROUTE_SCHEMA,
    ActiveRoute,
    CycleRule,
    LayoverSpec,
    RepeatingRoute,
    compiled_at,
    fly_filed,
    is_repeating,
    route_at,
)

__all__ = [
    "FILED_ROUTE_SCHEMA",
    "REPEATING_ROUTE_SCHEMA",
    "ActiveRoute",
    "CompiledRoute",
    "CycleRule",
    "LayoverSpec",
    "NotAtOrigin",
    "RepeatingRoute",
    "Route",
    "RouteGraph",
    "RouteLeg",
    "body_resolver",
    "compile_route",
    "compiled_at",
    "fly_filed",
    "fly_filed_route",
    "from_filed",
    "is_repeating",
    "plan_route",
    "plan_route_multi",
    "resolve_fleet",
    "resolve_fleet_junctions",
    "resolve_route",
    "route_at",
    "route_graph",
    "ship_from_artifact",
    "ship_from_transponder",
    "simulation_for_route",
    "speed_class",
    "to_filed",
]
