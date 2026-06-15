"""des — the lazy, deterministic discrete-event simulation core.

The engine's execution substrate (Phase 2b re-founding). Filed segments become
boundary **events**; ``state(T)`` replays events up to ``T`` then evaluates the
active segment analytically — preserving Phase 1's zero-drift, no-loop, fully
reproducible behaviour while structurally admitting the resolver-fixed,
open-ended boundaries the Phase 2c wormhole queue needs.

The math libraries (``ephemeris``, ``kinematics``) are unchanged inputs; this
package owns only the event model and the replay.
"""

from .core import ShipState, Simulation
from .event import Event, EventQueue
from .model import (
    SEGMENT_KINDS,
    OpenEndedSegment,
    UnknownSegmentKind,
    body_position,
    evaluate,
    segment_end,
)

__all__ = [
    "SEGMENT_KINDS",
    "Event",
    "EventQueue",
    "OpenEndedSegment",
    "ShipState",
    "Simulation",
    "UnknownSegmentKind",
    "body_position",
    "evaluate",
    "segment_end",
]
