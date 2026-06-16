"""The lazy, deterministic discrete-event simulation.

A :class:`Simulation` holds a ship's ordered segments plus the terminal context
(origin/final system + body). ``state(when)`` **replays events up to ``when`` then
evaluates the active segment analytically** — the model that keeps Phase 1's
zero-drift, no-loop guarantees while admitting the statefulness queues will need
(Phase 2c).

There is no per-tick loop: events are sparse (one per segment boundary), so
``advance_to`` pops at most one event per boundary and stops at the first event
past ``when``. ``state`` is a pure function of ``(segments, context, when)`` —
same inputs and same ``when`` give the same answer, always.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hvsim.kinematics import ZERO, Vec3

from .event import Event, EventQueue
from .model import BodyResolver, body_position, evaluate, segment_end
from .segment import Segment


@dataclass(frozen=True)
class ShipState:
    """Where the ship is at a queried instant (SI units).

    ``frame`` is ``"heliocentric"`` (position is in ``system``'s frame) or
    ``"galactic"`` (an interstellar ``hyper_cruise`` leg; ``system`` is None).
    """

    when: datetime
    position: Vec3
    velocity: Vec3
    phase: str  # predeparture | transit | layover | hyper_cruise | wormhole_transit | arrived
    segment_seq: int | None
    eta: datetime | None  # end of the current segment / overall arrival
    system: str | None = None
    frame: str = "heliocentric"


def _context(segment: Segment) -> tuple[str | None, str]:
    """The (system, frame) a segment's position is reported in."""
    if segment.kind == "hyper_cruise":
        return None, "galactic"
    if segment.kind == "wormhole_transit":
        return segment.to_system, "heliocentric"
    return segment.system, "heliocentric"


@dataclass(frozen=True)
class Simulation:
    """Executes one ship's filed segments via deterministic event replay."""

    segments: tuple[Segment, ...]
    depart_at: datetime
    origin_system: str | None
    origin_body: str
    final_system: str | None
    final_body: str | None
    resolve_body: BodyResolver | None = field(default=None, compare=False)

    def _at(self, system: str | None, body: str, when: datetime) -> Vec3:
        if self.resolve_body is not None and system is not None:
            return self.resolve_body(system, body, when)
        return body_position(body, when)

    def _queue(self) -> EventQueue:
        """An 'enter' event at each segment's start, time-ordered (tie: seq)."""
        q = EventQueue()
        for seg in self.segments:
            q.push(Event(seg.t_start, seg.seq, "enter", seg))
        return q

    def advance_to(self, when: datetime) -> Segment | None:
        """Replay events up to ``when``; return the active segment (or None).

        Pops 'enter' events in time order, stopping at the first event past
        ``when`` — so the active segment is the last one entered. Returns None
        when no segment has started yet (pre-departure).
        """
        q = self._queue()
        active: Segment | None = None
        while q and (head := q.peek()) is not None and head.t <= when:
            event = q.pop()
            # Applying an 'enter' event makes its segment active. This is where a
            # resolver would fix an open-ended predecessor's boundary and schedule
            # the real 'enter'; for today's closed segments the schedule is exact.
            active = event.segment
        return active

    def state(self, when: datetime) -> ShipState:
        """The ship's state at absolute time ``when``."""
        active = self.advance_to(when)

        if active is None:
            # No segment entered yet — sitting at the origin body.
            origin = self._at(self.origin_system, self.origin_body, when)
            return ShipState(
                when, origin, ZERO, "predeparture", None, self.depart_at, self.origin_system
            )

        end = segment_end(active, when)
        if when < end:
            position, velocity, phase = evaluate(active, when, self.resolve_body)
            system, frame = _context(active)
            return ShipState(when, position, velocity, phase, active.seq, end, system, frame)

        # Past the last segment's end (no successor entered) — docked at the
        # final body of the final system.
        final_body = self.final_body if self.final_body is not None else self.origin_body
        position = self._at(self.final_system, final_body, when)
        return ShipState(when, position, ZERO, "arrived", None, None, self.final_system)

    def navigable_location(self, when: datetime) -> tuple[str | None, str | None] | None:
        """The ship's current navigable point as ``(system, body)``, or None.

        A ship can file a new route only from a navigable point — at rest at a
        body. Keyed on **phase**, not raw speed (a ``wormhole_transit`` reports
        speed 0 yet is mid-transit, so it is *not* navigable):

        - ``predeparture`` → the origin body; ``layover`` → the layover body;
          ``arrived`` → the final body — all navigable.
        - ``transit`` / ``hyper_cruise`` / ``wormhole_transit`` → None (in motion).
        """
        active = self.advance_to(when)
        if active is None:
            return (self.origin_system, self.origin_body)  # predeparture
        if when >= segment_end(active, when):
            return (self.final_system, self.final_body)  # arrived
        if active.kind == "layover":
            return (active.system, active.body)
        return None  # transit / hyper_cruise / wormhole_transit — under way
