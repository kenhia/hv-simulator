"""flightplan — compile filed flight plans into absolute-time Segment rows.

Turns ordered waypoints + layovers into a sequence of closed-form trajectory
segments so that state(t) is a lookup plus one kinematics evaluation. In-memory
domain objects for now; persistence arrives with the API sprint (M4).
"""

from .plan import (
    CompiledPlan,
    FlightPlan,
    Segment,
    ShipState,
    Waypoint,
    compile_plan,
    state_at,
)
from .ship import Ship

__all__ = [
    "CompiledPlan",
    "FlightPlan",
    "Segment",
    "Ship",
    "ShipState",
    "Waypoint",
    "compile_plan",
    "state_at",
]
