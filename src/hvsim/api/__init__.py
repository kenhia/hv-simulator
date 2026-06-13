"""api — FastAPI service exposing ships, bodies, flight plans, and the clock.

Thin HTTP layer over the pure domain code; converts SI internals to km/AU and
human-readable durations at the boundary. (Sprint 004+.)
"""
