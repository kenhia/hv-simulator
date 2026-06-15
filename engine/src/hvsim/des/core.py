"""The lazy, deterministic discrete-event simulation.

A :class:`Simulation` holds a ship's ordered segments plus the terminal context
(origin body before departure, final body after arrival). ``state(when)``
**replays events up to ``when`` then evaluates the active segment analytically** —
the model that keeps Phase 1's zero-drift, no-loop guarantees while admitting the
statefulness queues will need (Phase 2c).

There is no per-tick loop: events are sparse (one per segment boundary), so
``advance_to`` pops at most one event per boundary and stops at the first event
past ``when``. ``state`` is a pure function of ``(segments, depart_at, bodies,
when)`` — same inputs and same ``when`` give the same answer, always; the replay
is rebuilt per call (memoisation would be a perf detail with no semantic effect).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hvsim.kinematics import ZERO, Vec3

from .event import Event, EventQueue
from .model import body_position, evaluate, segment_end


@dataclass(frozen=True)
class ShipState:
    """Where the ship is at a queried instant (SI units)."""

    when: datetime
    position: Vec3
    velocity: Vec3
    phase: str  # "predeparture" | "transit" | "layover" | "arrived"
    segment_seq: int | None
    eta: datetime | None  # end of the current segment / overall arrival


@dataclass(frozen=True)
class Simulation:
    """Executes one ship's filed segments via deterministic event replay."""

    segments: tuple[Any, ...]
    depart_at: datetime
    origin_body: str
    final_body: str | None

    def _queue(self) -> EventQueue:
        """An 'enter' event at each segment's start, time-ordered (tie: seq)."""
        q = EventQueue()
        for seg in self.segments:
            q.push(Event(seg.t_start, seg.seq, "enter", seg))
        return q

    def advance_to(self, when: datetime) -> Any | None:
        """Replay events up to ``when``; return the active segment (or None).

        Pops 'enter' events in time order, stopping at the first event past
        ``when`` — so the active segment is the last one entered. Returns None
        when no segment has started yet (pre-departure).
        """
        q = self._queue()
        active = None
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
            origin = body_position(self.origin_body, when)
            return ShipState(when, origin, ZERO, "predeparture", None, self.depart_at)

        end = segment_end(active, when)
        if when < end:
            position, velocity, phase = evaluate(active, when)
            return ShipState(when, position, velocity, phase, active.seq, end)

        # Past the last segment's end (no successor entered) — docked at the
        # final body.
        final = self.final_body if self.final_body is not None else self.origin_body
        return ShipState(when, body_position(final, when), ZERO, "arrived", None, None)
