"""The Segment — the discrete-event core's unit of execution.

One contiguous piece of a route in absolute time, of a closed :data:`SEGMENT_KINDS`
kind. In-system kinds (``transit``, ``layover``) live in a system's heliocentric
frame; inter-system kinds (``hyper_cruise``, ``wormhole_transit``) added in Sprint
014 carry the extra context the multi-mode route compiler needs:

- ``system`` — the system an in-system segment plays out in (heliocentric frame).
- ``trajectory`` — the closed-form n-space run for a ``transit``.
- ``body`` — the body a ``layover`` holds station at.
- ``from_pos`` / ``to_pos`` — galactic-frame endpoints (metres) of a
  ``hyper_cruise`` so position interpolates along the interstellar line.
- ``from_system`` / ``to_system`` — endpoints of a hyper or wormhole leg; a
  ``wormhole_transit`` reports arrival in ``to_system``.
- ``junction`` / ``queue_ahead`` — a ``wormhole_queue`` segment (Sprint 019): the
  junction the ship waits at, and the sorted transit-open instants of everything
  ahead of it once the fleet resolver has fixed the queue (used for ``position``).
  Open-ended (``t_end is None``) until the resolver runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hvsim.kinematics import Trajectory, Vec3


@dataclass(frozen=True)
class Segment:
    """One contiguous piece of a compiled route, in absolute time."""

    seq: int
    kind: str  # see hvsim.des.model.SEGMENT_KINDS
    t_start: datetime
    t_end: datetime | None  # None => open-ended, fixed by a resolver (Phase 2c)
    trajectory: Trajectory | None = None  # transit
    body: str | None = None  # layover
    system: str | None = None  # in-system frame this segment is expressed in
    from_pos: Vec3 | None = None  # hyper_cruise: galactic-frame start (metres)
    to_pos: Vec3 | None = None  # hyper_cruise: galactic-frame end (metres)
    from_system: str | None = None  # hyper / wormhole origin
    to_system: str | None = None  # hyper / wormhole destination
    junction: str | None = None  # wormhole_queue: the junction being transited
    queue_ahead: tuple[datetime, ...] | None = None  # wormhole_queue: transit-opens ahead

    @property
    def duration_s(self) -> float:
        assert self.t_end is not None
        return (self.t_end - self.t_start).total_seconds()
