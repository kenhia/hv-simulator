"""The segment/event/mode model — closed kinds with exhaustive dispatch.

This is the seam the rest of Phase 2 grows from. The dispatch is intentionally
exhaustive: an unrecognised kind raises rather than silently doing nothing — the
Python stand-in for the compile-time ``match`` exhaustiveness an eventual Rust
port would give us.

Two functions define a segment's behaviour:

- :func:`segment_end` resolves *when* a segment ends. Closed segments carry a
  fixed ``t_end``; this is the **resolver seam** — an open-ended segment (the
  Phase 2c wormhole queue) leaves ``t_end`` unset and a resolver fixes it at
  arrival. No resolver exists yet, so an open-ended segment raises.
- :func:`evaluate` answers *where the ship is* within an active segment.

Segment kinds (Sprint 014 added the two inter-system kinds):

- ``transit`` — closed-form n-space run (brachistochrone/coast) in a system frame.
- ``layover`` — holding station at a body (tracks the moving body).
- ``hyper_cruise`` — straight-line interstellar leg at a band's apparent velocity,
  expressed in the galactic frame.
- ``wormhole_queue`` — waiting in a junction's transit queue (Sprint 019); an
  open-ended segment fixed by the fleet queue resolver. Reports phase ``queued``
  with a queue position; the ship holds at the nexus in the origin system.
- ``wormhole_transit`` — near-instant junction translation; reports arrival in
  the destination system.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from hvsim.ephemeris import heliocentric_position
from hvsim.kinematics import ZERO, Vec3

# The closed set of segment kinds. Each addition must extend the dispatch below
# too, or evaluation raises.
SEGMENT_KINDS = ("transit", "layover", "hyper_cruise", "wormhole_queue", "wormhole_transit")

# A position resolver maps (system_id, body_id, when) -> heliocentric Vec3 (m).
BodyResolver = Callable[[str, str, datetime], Vec3]


class UnknownSegmentKind(Exception):
    """A segment carried a kind not in :data:`SEGMENT_KINDS`."""


class OpenEndedSegment(Exception):
    """A segment with no fixed ``t_end`` was reached but no resolver can fix it.

    The structural placeholder for the Phase 2c wormhole-queue resolver: the
    model admits open-ended boundaries, but none can be resolved yet.
    """


def body_position(body: str, when: datetime) -> Vec3:
    """Heliocentric (Sol) position of ``body`` at ``when`` (SI metres)."""
    return Vec3(*heliocentric_position(body, when))


def _resolve(segment: Any, when: datetime, resolve_body: BodyResolver | None) -> Vec3:
    """Resolve a body's position, defaulting to the Sol JPL ephemeris."""
    assert segment.body is not None
    if resolve_body is not None and segment.system is not None:
        return resolve_body(segment.system, segment.body, when)
    return body_position(segment.body, when)


def segment_end(segment: Any, when: datetime) -> datetime:
    """Resolve a segment's end instant.

    Closed segments return their fixed ``t_end``. An open-ended segment
    (``t_end is None``) is where a stateful resolver would fix the boundary at
    arrival; until Phase 2c there is none, so it raises.
    """
    if segment.t_end is not None:
        return segment.t_end
    raise OpenEndedSegment(segment.kind)


def evaluate(
    segment: Any, when: datetime, resolve_body: BodyResolver | None = None
) -> tuple[Vec3, Vec3, str]:
    """Return ``(position, velocity, phase)`` for an active segment at ``when``.

    Positions are in the segment's frame: heliocentric (per ``system``) for
    ``transit``/``layover``/``wormhole_transit`` arrival, galactic for
    ``hyper_cruise``.
    """
    if segment.kind == "transit":
        assert segment.trajectory is not None
        st = segment.trajectory.state((when - segment.t_start).total_seconds())
        return st.position, st.velocity, "transit"
    if segment.kind == "layover":
        return _resolve(segment, when, resolve_body), ZERO, "layover"
    if segment.kind == "hyper_cruise":
        # Accel/coast/decel in the galactic frame (apparent units). Same closed-form
        # trajectory as a transit, just reported in the galactic frame.
        assert segment.trajectory is not None
        st = segment.trajectory.state((when - segment.t_start).total_seconds())
        return st.position, st.velocity, "hyper_cruise"
    if segment.kind == "wormhole_queue":
        # Holding at the nexus in the origin system, waiting for a transit slot.
        # Reported at the star centre (origin of the from_system frame); the
        # queue position is read separately via :func:`queue_position`.
        return ZERO, ZERO, "queued"
    if segment.kind == "wormhole_transit":
        # Near-instant translation; reported at the destination star centre
        # (origin of the to_system frame). Position precision is immaterial.
        return ZERO, ZERO, "wormhole_transit"
    raise UnknownSegmentKind(segment.kind)


def queue_position(segment: Any, when: datetime) -> int | None:
    """Queue position (1 == next to transit) of a resolved ``wormhole_queue`` segment.

    ``#N`` = (transit-opens still ahead at ``when``) + 1; counts down to the pop.
    Returns None for any other kind or before the resolver has run.
    """
    if segment.kind != "wormhole_queue" or segment.queue_ahead is None:
        return None
    return sum(1 for t in segment.queue_ahead if t > when) + 1
