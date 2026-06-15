"""Prometheus exposition for ship telemetry.

A fresh ``CollectorRegistry`` is built per scrape from the supplied ship states,
so there is no module-global mutation and no stale series — the scrape is a pure
render of "where is everything now". The state itself is computed analytically
upstream (same path as ``/ships``); nothing here runs a loop.
"""

from __future__ import annotations

from datetime import datetime

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

from .schemas import StateOut

__all__ = ["CONTENT_TYPE_LATEST", "render"]

# Phases we always emit a count for (so panels don't gap when a phase is empty).
_PHASES = ("idle", "predeparture", "transit", "layover", "arrived")


def render(
    states: list[tuple[str, str, StateOut]],
    when: datetime,
    rate: float,
    bodies_total: int,
) -> bytes:
    """Render Prometheus exposition for the fleet. ``states`` is (ship_id, name, state)."""
    reg = CollectorRegistry()
    ship_labels = ["ship_id", "name"]

    speed_c = Gauge(
        "hvsim_ship_speed_fraction_c", "Ship speed as a fraction of c", ship_labels, registry=reg
    )
    speed_kms = Gauge("hvsim_ship_speed_km_s", "Ship speed in km/s", ship_labels, registry=reg)
    pct = Gauge("hvsim_ship_percent_complete", "Trip completion (0-1)", ship_labels, registry=reg)
    dist = Gauge(
        "hvsim_ship_distance_to_destination_km",
        "Straight-line distance to destination (km)",
        ship_labels,
        registry=reg,
    )
    eta = Gauge(
        "hvsim_ship_eta_seconds",
        "Seconds until arrival (0 if idle/arrived)",
        ship_labels,
        registry=reg,
    )
    info = Gauge(
        "hvsim_ship_info",
        "Ship state (always 1); carries phase/destination labels",
        ["ship_id", "name", "phase", "destination"],
        registry=reg,
    )
    ships_by_phase = Gauge("hvsim_ships", "Ship count by phase", ["phase"], registry=reg)
    bodies = Gauge("hvsim_bodies_total", "Number of known bodies", registry=reg)
    clock_rate = Gauge("hvsim_clock_rate", "SimClock rate multiplier", registry=reg)
    sim_time = Gauge("hvsim_sim_time_seconds", "Simulated time (unix seconds)", registry=reg)

    phase_counts: dict[str, int] = dict.fromkeys(_PHASES, 0)
    for ship_id, name, st in states:
        speed_c.labels(ship_id, name).set(st.velocity.fraction_c)
        speed_kms.labels(ship_id, name).set(st.velocity.speed_km_s)
        pct.labels(ship_id, name).set(st.percent_complete or 0.0)
        dist.labels(ship_id, name).set(st.distance_to_destination_km or 0.0)
        eta_s = max(0.0, (st.eta - when).total_seconds()) if st.eta else 0.0
        eta.labels(ship_id, name).set(eta_s)
        info.labels(ship_id, name, st.phase, st.destination or "none").set(1)
        phase_counts[st.phase] = phase_counts.get(st.phase, 0) + 1

    for phase in _PHASES:
        ships_by_phase.labels(phase).set(phase_counts[phase])
    bodies.set(bodies_total)
    clock_rate.set(rate)
    sim_time.set(when.timestamp())

    return generate_latest(reg)
