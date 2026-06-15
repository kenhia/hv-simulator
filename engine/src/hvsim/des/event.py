"""The event queue — the heart of the discrete-event core.

Events are segment boundaries in absolute time. The queue pops them in time
order so ``advance_to(T)`` can replay the world up to an instant without a
per-tick loop. Ordering is fully deterministic: ties on time break on a stable
integer key (segment sequence), so the same inputs always replay identically.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(order=True)
class Event:
    """A scheduled moment the simulation must act on.

    Only ``t`` and ``order`` participate in comparison (the heap key); ``kind``
    and ``segment`` are payload. ``order`` is the deterministic tiebreak for
    events that share an instant (e.g. a zero-length layover, or one segment's
    end coinciding with the next's start).
    """

    t: datetime
    order: int
    kind: str = field(compare=False)
    segment: Any = field(compare=False, default=None)


class EventQueue:
    """A min-heap of :class:`Event` ordered by ``(t, order)``."""

    def __init__(self) -> None:
        self._heap: list[Event] = []

    def push(self, event: Event) -> None:
        heapq.heappush(self._heap, event)

    def pop(self) -> Event:
        return heapq.heappop(self._heap)

    def peek(self) -> Event | None:
        return self._heap[0] if self._heap else None

    def __bool__(self) -> bool:
        return bool(self._heap)

    def __len__(self) -> int:
        return len(self._heap)
