"""SimClock — the single time source for the simulator.

``now()`` maps real elapsed time onto simulated time via an epoch anchor and a
``rate`` multiplier. Production runs at rate 1.0 (real time — the whole point of
the project); dev and tests raise the rate or move the epoch to fast-forward a
multi-hour trip. Domain code never calls the wall clock directly — it goes
through a SimClock.

Minimal for Sprint 002 (the ephemeris CLI's "now" goes through it); jump/rate
mutation helpers arrive with the flight-plan sprint that needs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


def _real_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SimClock:
    """Maps real time to sim time: ``sim_epoch + (real_now - real_epoch) * rate``.

    With all defaults this is an ordinary real-time UTC clock.
    """

    rate: float = 1.0
    sim_epoch: datetime | None = None
    real_epoch: datetime | None = None

    def __post_init__(self) -> None:
        if self.real_epoch is None:
            self.real_epoch = _real_now()
        if self.sim_epoch is None:
            self.sim_epoch = self.real_epoch

    def now(self) -> datetime:
        """Current simulated time as a timezone-aware UTC datetime."""
        assert self.real_epoch is not None and self.sim_epoch is not None
        elapsed = (_real_now() - self.real_epoch).total_seconds()
        return self.sim_epoch + timedelta(seconds=elapsed * self.rate)

    def _reanchor(self, sim_time: datetime) -> None:
        """Pin sim time to ``sim_time`` as of the real instant now."""
        self.sim_epoch = sim_time
        self.real_epoch = _real_now()

    def set_rate(self, rate: float) -> None:
        """Change the rate multiplier, keeping the current sim time continuous."""
        self._reanchor(self.now())
        self.rate = rate

    def jump_to(self, sim_time: datetime) -> None:
        """Jump sim time to an absolute instant (dev/test fast-forward)."""
        self._reanchor(sim_time)

    def advance(self, delta: timedelta) -> None:
        """Jump sim time forward (or back) by ``delta`` (dev/test fast-forward)."""
        self._reanchor(self.now() + delta)
