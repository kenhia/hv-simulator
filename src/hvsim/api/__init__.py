"""api — FastAPI service exposing ships, bodies, flight plans, and the clock.

Thin HTTP layer over the pure domain code; converts SI internals to km/AU and
human-readable durations at the boundary. Run with
``uvicorn --factory hvsim.api.app:create_app``.
"""

from .app import create_app

__all__ = ["create_app"]
