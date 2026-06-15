"""clock — SimClock, the only time source (epoch offset + rate multiplier).

Production runs at rate 1.0; the rate/jump controls exist for dev and tests so a
multi-hour trip can be fast-forwarded. Domain code never calls now() directly.
"""

from .clock import SimClock

__all__ = ["SimClock"]
