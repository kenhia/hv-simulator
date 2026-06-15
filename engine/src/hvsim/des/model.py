"""The segment/event/mode model — closed kinds with exhaustive dispatch.

This is the seam the rest of Phase 2 grows from. Today there are two segment
kinds, both closed-form (``transit``, ``layover``). The dispatch is intentionally
exhaustive: an unrecognised kind raises rather than silently doing nothing — the
Python stand-in for the compile-time ``match`` exhaustiveness an eventual Rust
port would give us.

Two functions define a segment's behaviour:

- :func:`segment_end` resolves *when* a segment ends. Closed segments carry a
  fixed ``t_end``; this is the **resolver seam** — an open-ended segment (the
  Phase 2c wormhole queue) leaves ``t_end`` unset and a resolver fixes it at
  arrival. No resolver exists yet, so an open-ended segment raises.
- :func:`evaluate` answers *where the ship is* within an active segment.

A segment is any object exposing ``seq``, ``kind``, ``t_start``, ``t_end``,
``trajectory`` (transit), and ``body`` (layover) — `flightplan.Segment` fits,
and the core stays free of a flightplan import (no cycle).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hvsim.ephemeris import heliocentric_position
from hvsim.kinematics import ZERO, Vec3

# The closed set of segment kinds. Phase 2b/2c extend this (hyper_cruise,
# wormhole_transit, wormhole_queue); each addition must extend the dispatch
# below too, or evaluation raises.
SEGMENT_KINDS = ("transit", "layover")


class UnknownSegmentKind(Exception):
    """A segment carried a kind not in :data:`SEGMENT_KINDS`."""


class OpenEndedSegment(Exception):
    """A segment with no fixed ``t_end`` was reached but no resolver can fix it.

    The structural placeholder for the Phase 2c wormhole-queue resolver: the
    model admits open-ended boundaries, but none can be resolved yet.
    """


def body_position(body: str, when: datetime) -> Vec3:
    """Heliocentric position of ``body`` at ``when`` (SI metres)."""
    return Vec3(*heliocentric_position(body, when))


def segment_end(segment: Any, when: datetime) -> datetime:
    """Resolve a segment's end instant.

    Closed segments return their fixed ``t_end``. An open-ended segment
    (``t_end is None``) is where a stateful resolver would fix the boundary at
    arrival; until Phase 2c there is none, so it raises.
    """
    if segment.t_end is not None:
        return segment.t_end
    raise OpenEndedSegment(segment.kind)


def evaluate(segment: Any, when: datetime) -> tuple[Vec3, Vec3, str]:
    """Return ``(position, velocity, phase)`` for an active segment at ``when``."""
    if segment.kind == "transit":
        assert segment.trajectory is not None
        st = segment.trajectory.state((when - segment.t_start).total_seconds())
        return st.position, st.velocity, "transit"
    if segment.kind == "layover":
        assert segment.body is not None
        return body_position(segment.body, when), ZERO, "layover"
    raise UnknownSegmentKind(segment.kind)
