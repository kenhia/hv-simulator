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
  ahead by arrival time (stable-key tiebreak), so two real ships interleave
  deterministically.

The junction is modelled as a single FCFS server (`JunctionServer`): items are
served back-to-back through their ``interval``; a ship's **transit-open** time is
when the server reaches it, and its **position(t)** counts the transit-opens
still ahead. Real ships and a ship's own phantom share one ordered timeline, so
position is consistent with the resolved time.

v1 simplification (documented): each real ship samples its *own* phantom
background; reals additionally serialise behind one another in time. Multi-
wormhole routes resolve queue-by-queue in global arrival order (a ship's later
junction arrival shifts with its earlier wait) — exact for the single-wormhole
routes that exist today.
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
    """A single junction's FCFS server, accumulating transits across ships."""

    junction_id: str
    coeff_a: float
    coeff_b: float
    buffer_s: float
    mean_depth: float
    seed: int = SIM_SEED
    busy_until: datetime | None = None
    _opens: list[datetime] = field(default_factory=list)  # all transit-opens so far, sorted

    def serve(self, arrival: datetime, mass_tons: float, ship_key: str) -> TransitResolution:
        """Resolve a ship arriving at ``arrival``; advance the server past it.

        The ship's phantom-ahead are served first (from when the junction is free
        of earlier real traffic), then the ship itself. Everything ahead of the
        ship's transit-open is its queue position.
        """
        free = arrival if self.busy_until is None else max(arrival, self.busy_until)
        ahead = [t for t in self._opens if t < free]  # earlier reals + their phantom

        # Phantom ships this ship finds ahead, serialised from `free`.
        for m in phantom_masses(self.seed, self.junction_id, ship_key, self.mean_depth):
            p_open = free
            ahead.append(p_open)
            self._opens.append(p_open)
            step = interval(m, self.coeff_a, self.coeff_b, self.buffer_s)
            free = p_open + timedelta(seconds=step)

        # The ship itself transits when the server reaches it, then busies the nexus.
        transit_open = free
        self._opens.append(transit_open)
        self._opens.sort()
        self.busy_until = transit_open + timedelta(
            seconds=interval(mass_tons, self.coeff_a, self.coeff_b, self.buffer_s)
        )
        ahead.sort()
        return TransitResolution(transit_open=transit_open, ahead_opens=tuple(ahead))
