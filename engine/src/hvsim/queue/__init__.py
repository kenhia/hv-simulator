"""Wormhole queue resolver — the first stateful resolver on the DES core.

A junction transit destabilises the nexus for ``interval = max(tau(M), buffer)``
seconds (``tau(M) = A*sqrt(M) + B*M^2``, M = tons transited), so transits at a
junction **serialise**. A ship reaching a junction joins a queue whose depth is
not knowable at filing time; its transit slot is fixed at arrival from the
junction's dynamic state. This module is the math + the fleet-level fold that
fixes the open-ended ``wormhole_queue`` segments compile_route emits.

Two sources of queue depth:

- **Phantom traffic** — each junction carries a fabricated ``traffic_intensity``
  (mean queue depth). On a ship's arrival the phantom ships ahead are a draw from
  Poisson(mean) with masses, a **pure function of (seed, junction, ship-key)** —
  so depth varies (quiet -> ~immediate; busy -> deep) but is fully reproducible.
- **Real ships** — other filed ships transiting the same junction serialise
  around one another on the junction's calendar, so two real ships interleave
  deterministically.

The junction is modelled as a **reservation calendar** (`JunctionServer`): each
ship books one contiguous block (its phantom back-to-back, then itself) into the
earliest gap at or after its arrival, and a booked block never moves. A ship's
**transit-open** time is when its own slot in that block comes up, and its
**position(t)** counts the transit-opens still ahead. Real ships and a ship's own
phantom share one ordered timeline, so position is consistent with the resolved
time.

Booking rather than a monotone cursor is what makes the schedule **stable**: the
fleet resolver folds routes in **filing** order, so a route filed later can never
perturb an earlier filer's slot (Sprint 039, #67) — while a ship arriving at an
idle nexus still transits at once rather than waiting on a slot booked further out.

v1 simplification (documented): each real ship samples its *own* phantom
background. Multi-wormhole routes resolve queue-by-queue along each route (a
ship's later junction arrival shifts with its earlier wait) — exact for the
single-wormhole routes that exist today.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# The one global source of "randomness". Same (seed, junction, ship) -> same draw,
# always; combined with the per-junction knob it is the only entropy in the fold.
SIM_SEED = 0x484F4E52  # "HONR"

# Typical phantom-ship displacement (tons): a lognormal around a freighter. Mass
# only bites tau above ~1e7 t, so for normal traffic interval == buffer; the draw
# exists so heavy convoys can matter later.
_PHANTOM_MASS_MEDIAN_T = 3.0e6
_PHANTOM_MASS_SIGMA = 0.6
# Fallback transiting-ship mass when a hull carries none (a plain in-system Ship).
DEFAULT_SHIP_MASS_T = 3.0e6


def tau(mass_tons: float, coeff_a: float, coeff_b: float) -> float:
    """Nexus destabilisation time (s) for transiting ``mass_tons``."""
    m = max(mass_tons, 0.0)
    return coeff_a * math.sqrt(m) + coeff_b * m * m


def interval(mass_tons: float, coeff_a: float, coeff_b: float, buffer_s: float) -> float:
    """Time the junction is unusable after a transit: ``max(tau(M), buffer)``."""
    return max(tau(mass_tons, coeff_a, coeff_b), buffer_s)


def _seed_int(seed: int, junction_id: str, ship_key: str) -> int:
    """A process-stable integer seed (Python's ``hash`` is salted, so use SHA)."""
    raw = f"{seed}|{junction_id}|{ship_key}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _poisson(rng: random.Random, mean: float) -> int:
    """Knuth's algorithm — a Poisson draw with the given mean (small means)."""
    if mean <= 0.0:
        return 0
    target = math.exp(-mean)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= target:
            return k
        k += 1


def phantom_masses(seed: int, junction_id: str, ship_key: str, mean_depth: float) -> list[float]:
    """The phantom ships a ship finds ahead on arrival: count ~ Poisson(mean), masses drawn.

    A pure function of ``(seed, junction, ship_key)`` — reproducible, never a
    constant. ``mean_depth`` is the junction's ``traffic_intensity`` knob.
    """
    rng = random.Random(_seed_int(seed, junction_id, ship_key))
    count = _poisson(rng, mean_depth)
    return [
        _PHANTOM_MASS_MEDIAN_T * math.exp(rng.gauss(0.0, _PHANTOM_MASS_SIGMA)) for _ in range(count)
    ]


@dataclass(frozen=True)
class Transit:
    """One occupant of a junction's serialised timeline (real ship or phantom).

    ``transponder`` is the real ship's id, or ``None`` for phantom traffic. The
    occupant is "present in the queue" over ``[arrival, transit_open)`` — for a
    phantom, ``arrival`` is the real ship it was drawn ahead of, so phantom only
    surface while that ship is actually queued.
    """

    transponder: str | None
    mass_tons: float
    arrival: datetime
    transit_open: datetime


@dataclass
class TransitResolution:
    """The resolved slot for one ship at a junction."""

    transit_open: datetime  # when the ship transits (instant) -> end of its queue wait
    ahead_opens: tuple[datetime, ...]  # transit-open instants of everything ahead, sorted

    def position(self, when: datetime) -> int:
        """Queue position at ``when``: 1 == next to transit; counts down to the pop.

        ``#N`` = (items still ahead at ``when``) + 1. At ``transit_open`` it is 1,
        then the ship pops through.
        """
        ahead = sum(1 for t in self.ahead_opens if t > when)
        return ahead + 1


@dataclass
class JunctionServer:
    """A single junction's server: a **reservation calendar** of transit blocks.

    Each served ship books one contiguous block — its phantom-ahead back-to-back,
    then itself — into the earliest gap at or after its arrival that no existing
    reservation overlaps. First-fit, so:

    - a reservation, once booked, **never moves** (Sprint 039, #67 — a ship filed
      later cannot push an earlier filer's slot), and
    - a ship arriving at an idle nexus transits immediately even if a later
      arrival has already booked a slot further out.

    Serving therefore no longer has to happen in arrival order; the fleet resolver
    folds in **filing** order and gets a schedule that is stable as ships are added.
    """

    junction_id: str
    coeff_a: float
    coeff_b: float
    buffer_s: float
    mean_depth: float
    seed: int = SIM_SEED
    # Booked [start, end) blocks, sorted and non-overlapping.
    _booked: list[tuple[datetime, datetime]] = field(default_factory=list)
    transits: list[Transit] = field(default_factory=list)  # every occupant (real + phantom)

    @property
    def opens(self) -> list[datetime]:
        """Every transit-open instant booked so far, sorted."""
        return sorted(t.transit_open for t in self.transits)

    def _first_fit(self, arrival: datetime, span_s: float) -> datetime:
        """Earliest start >= ``arrival`` where a ``span_s`` block clears every booking."""
        span = timedelta(seconds=span_s)
        start = arrival
        for b_start, b_end in self._booked:  # sorted, non-overlapping
            if b_end <= start:
                continue
            if b_start - start >= span:  # the gap before this booking is big enough
                return start
            start = b_end
        return start

    def serve(self, arrival: datetime, mass_tons: float, ship_key: str) -> TransitResolution:
        """Resolve a ship arriving at ``arrival``; book its block on the calendar.

        The ship's phantom-ahead transit first (they are what it finds in front of
        it), then the ship itself, then the nexus destabilises for its interval.
        Everything opening before the ship's own transit-open is its queue position.
        """
        phantom = phantom_masses(self.seed, self.junction_id, ship_key, self.mean_depth)
        steps = [interval(m, self.coeff_a, self.coeff_b, self.buffer_s) for m in phantom]
        span = sum(steps) + interval(mass_tons, self.coeff_a, self.coeff_b, self.buffer_s)

        start = self._first_fit(arrival, span)
        self._booked.append((start, start + timedelta(seconds=span)))
        self._booked.sort()

        # Phantom share the real ship's arrival, so they only surface in a snapshot
        # while that ship is actually queued.
        cursor, ahead = start, [t for t in self.opens if t < start]
        for m, step in zip(phantom, steps, strict=True):
            ahead.append(cursor)
            self.transits.append(Transit(None, m, arrival, cursor))
            cursor += timedelta(seconds=step)

        transit_open = cursor
        self.transits.append(Transit(ship_key, mass_tons, arrival, transit_open))
        ahead.sort()
        return TransitResolution(transit_open=transit_open, ahead_opens=tuple(ahead))

    def ahead_of(self, transit_open: datetime) -> tuple[datetime, ...]:
        """Every booked transit-open strictly before ``transit_open``, sorted.

        The authoritative "what is in front of me" once the whole fleet has been
        folded — a first-fit insert can land a later-served ship *ahead* of an
        earlier-served one, so positions are repaired from this at the end of the
        fold rather than frozen at serve time.
        """
        return tuple(t for t in self.opens if t < transit_open)

    def snapshot(self, when: datetime) -> list[Transit]:
        """The queue present at ``when``: occupants with arrival <= when < transit_open.

        Ordered by transit-open (front of the queue first); the caller assigns
        positions (``#1`` = next to transit).
        """
        present = [t for t in self.transits if t.arrival <= when < t.transit_open]
        present.sort(key=lambda t: t.transit_open)
        return present
