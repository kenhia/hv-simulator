"""Repeating routes — a ship that *lives on a loop* (#59, design in sprints/035).

A **repeating route** is a round trip a ship flies forever (or N times): file it
once and the simulator never needs the next flight plan filed by hand. Couriers
shuttle, transports cycle, and the galaxy stops looking like a set of one-shot
deliveries.

The load-bearing constraint is the project's: **there is no background tick.**
Like ``state_at``, a repeating route is *lazy and analytic* — a template plus a
start time deterministically define every cycle, and a query at time T walks to
the cycle covering T and compiles **just that one**. Storage stays tiny (the
template and a seed, never per-trip rows), and re-querying the same T gives the
same answer, always.

Three deterministic pieces make that work:

- A cycle is an ordinary multi-leg :class:`~hvsim.route.Route` back to the
  origin, compiled by :func:`~hvsim.route.compile_route`. Cycle *N+1* departs the
  instant cycle *N* ends, so boundaries chain.
- **Layovers are derived, not stored.** Each stop carries a range; the value for
  a given cycle is ``min + frac(hash(seed, cycle, stop)) * (max - min)``. It
  varies (so the loop doesn't look mechanical) but is reproducible across
  restarts.
- **Cycle rules** cover the "every 5th trip, a 12 h crew rotation" flavour: a
  small list of ``every-N`` overrides on one stop's layover. v1 keeps the rule
  list deliberately dumb — a richer DSL is deferred.

Walking to cycle 400 means compiling 400 cycles, so boundaries are memoized per
filed document (:func:`route_at`). That is pure memoization of a deterministic
function — a cache miss costs time, never correctness.
"""

from __future__ import annotations

import hashlib
import threading
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from hvsim.des import Simulation
from hvsim.flightplan import Ship
from hvsim.universe import Universe

from .plan import (
    CompiledRoute,
    NotAtOrigin,
    Route,
    RouteLeg,
    compile_route,
    resolve_route,
    ship_from_transponder,
)
from .plan import from_filed as one_shot_from_filed

REPEATING_ROUTE_SCHEMA = "hvsim.repeating-route/v1"

# A runaway guard: a template whose cycles are absurdly short (or a start_at in
# the deep past) must not walk forever. ~a decade of daily round trips.
MAX_CYCLE_WALK = 10_000


class CycleWalkTooLong(Exception):
    """A repeating route needed more than :data:`MAX_CYCLE_WALK` cycles to reach T."""


@dataclass(frozen=True)
class LayoverSpec:
    """A stop's layover as a range; ``min_s == max_s`` is a fixed layover."""

    min_s: float
    max_s: float

    @classmethod
    def fixed(cls, seconds: float) -> LayoverSpec:
        return cls(seconds, seconds)


@dataclass(frozen=True)
class CycleRule:
    """Override one stop's layover on every ``every``-th cycle (1-based)."""

    every: int
    stop: int  # index into the cycle's legs
    layover_s: float


@dataclass(frozen=True)
class RepeatingRoute:
    """A round trip plus the rules for repeating it.

    ``legs`` describe **one** cycle and must return the ship to its origin;
    ``layovers`` is index-aligned with them (a missing entry means no layover).
    ``cycles`` is None for "forever" — the alive default — or an integer, after
    which the ship stays put at the origin.
    """

    ship: Ship
    transponder: str
    origin_system: str
    origin_body: str
    legs: list[RouteLeg]
    start_at: datetime
    layovers: list[LayoverSpec] = field(default_factory=list)
    seed: int = 0
    cycles: int | None = None
    rules: tuple[CycleRule, ...] = ()


def layover_for(rep: RepeatingRoute, cycle: int, stop: int) -> timedelta:
    """The layover at ``stop`` on ``cycle`` (0-based) — deterministic, never stored.

    A matching :class:`CycleRule` wins; otherwise the value is drawn from the
    stop's range by hashing ``(seed, cycle, stop)``, so the same query always
    yields the same wait.
    """
    for rule in rep.rules:
        if rule.stop == stop and rule.every > 0 and (cycle + 1) % rule.every == 0:
            return timedelta(seconds=rule.layover_s)
    if stop >= len(rep.layovers):
        return timedelta(0)
    spec = rep.layovers[stop]
    if spec.max_s <= spec.min_s:
        return timedelta(seconds=spec.min_s)
    raw = hashlib.sha256(f"{rep.seed}|{cycle}|{stop}".encode()).digest()[:8]
    frac = int.from_bytes(raw, "big") / 2**64  # in [0, 1)
    return timedelta(seconds=spec.min_s + frac * (spec.max_s - spec.min_s))


def cycle_route(rep: RepeatingRoute, cycle: int, depart_at: datetime) -> Route:
    """The ordinary :class:`Route` for one cycle, with its layovers filled in."""
    legs = [
        RouteLeg(lg.mode, lg.to_system, lg.to_body, layover_for(rep, cycle, i))
        for i, lg in enumerate(rep.legs)
    ]
    return Route(rep.ship, rep.origin_system, rep.origin_body, legs, depart_at)


def compile_cycle(
    rep: RepeatingRoute, cycle: int, depart_at: datetime, u: Universe
) -> CompiledRoute:
    """Compile one cycle against the artifact — **unresolved**, like any route.

    A wormhole leg leaves its queue segment open-ended for the fleet resolver, so
    the caller resolves exactly as it would a one-shot route.
    """
    return compile_route(cycle_route(rep, cycle, depart_at), u)


def cycle_end(rep: RepeatingRoute, cycle: int, depart_at: datetime, u: Universe) -> datetime:
    """When a cycle ends — and so when the next one departs.

    A cycle crossing a junction has to have a *closed* end or the loop could not
    chain, so its queue is resolved **in isolation** (phantom traffic only, seeded
    by the ship's transponder). That keeps the boundary a pure function of the
    template; fleet-level interleaving is applied to the active cycle at query
    time and can shift it a little relative to the boundary.
    """
    compiled = compile_cycle(rep, cycle, depart_at, u)
    if any(seg.kind == "wormhole_queue" for seg in compiled.segments):
        compiled = resolve_route(compiled, u, rep.transponder)
    return compiled.arrival


# Memoized cycle boundaries, per artifact: template hash -> [depart of cycle 0, 1,
# ...]. The boundaries are a pure function of (template, artifact), so this only
# ever saves recompilation — a cold cache costs time, never correctness. Entries
# die with the Universe; a template that stops being flown leaves one behind.
_boundaries: weakref.WeakKeyDictionary[Universe, dict[str, list[datetime]]] = (
    weakref.WeakKeyDictionary()
)
_lock = threading.Lock()


def _template_key(rep: RepeatingRoute) -> str:
    parts = [
        rep.transponder,
        rep.origin_system,
        rep.origin_body,
        rep.start_at.isoformat(),
        str(rep.seed),
        str(rep.cycles),
        ";".join(f"{lg.mode},{lg.to_system},{lg.to_body}" for lg in rep.legs),
        ";".join(f"{s.min_s},{s.max_s}" for s in rep.layovers),
        ";".join(f"{r.every},{r.stop},{r.layover_s}" for r in rep.rules),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _starts(rep: RepeatingRoute, u: Universe) -> list[datetime]:
    """The memoized cycle-departure instants for this template (at least cycle 0)."""
    with _lock:
        per_artifact = _boundaries.setdefault(u, {})
        return per_artifact.setdefault(_template_key(rep), [rep.start_at])


def route_at(rep: RepeatingRoute, when: datetime, u: Universe) -> tuple[int, CompiledRoute]:
    """The active ``(cycle_index, CompiledRoute)`` at ``when``.

    Walks cycle boundaries from ``start_at`` — each cycle departing where the last
    ended — until it finds the one covering ``when``, and compiles **only** that
    cycle. Before ``start_at`` this is cycle 0 (the ship is pre-departure); past
    the last cycle of a finite route it is the final cycle, so the ship reports
    ``arrived`` at its origin and stays there. Nothing is simulated in between.
    """
    starts = _starts(rep, u)
    cycle = 0
    while True:
        if rep.cycles is not None and cycle >= rep.cycles:
            cycle = max(rep.cycles - 1, 0)  # finite route: hold at the last cycle
            break
        if cycle + 1 < len(starts):
            end = starts[cycle + 1]  # boundary already known -> nothing to compile
        else:
            end = cycle_end(rep, cycle, starts[cycle], u)
            with _lock:
                if cycle + 1 >= len(starts):
                    starts.append(end)
        if when < end:
            break
        cycle += 1
        if cycle > MAX_CYCLE_WALK:
            raise CycleWalkTooLong(
                f"{cycle} cycles from {rep.start_at.isoformat()} to reach {when}"
            )

    return cycle, compile_cycle(rep, cycle, starts[cycle], u)


# -- The filed document (same seam as a one-shot route) --------------------------


def to_filed(rep: RepeatingRoute) -> dict:
    """Serialize to the ``hvsim.repeating-route/v1`` document the engine reloads."""
    return {
        "schema": REPEATING_ROUTE_SCHEMA,
        "ship": rep.transponder,
        "origin": {"system": rep.origin_system, "body": rep.origin_body},
        "start_at": rep.start_at.isoformat(),
        "legs": [
            {"mode": lg.mode, "to_system": lg.to_system, "to_body": lg.to_body} for lg in rep.legs
        ],
        "repeat": {
            "layovers": [{"min_s": s.min_s, "max_s": s.max_s} for s in rep.layovers],
            "cycles": rep.cycles,
            "seed": rep.seed,
            "rules": [
                {"every": r.every, "stop": r.stop, "layover_s": r.layover_s} for r in rep.rules
            ],
        },
    }


def from_filed(doc: dict, u: Universe) -> RepeatingRoute:
    """Rebuild a :class:`RepeatingRoute` from its filed document."""
    if doc.get("schema") != REPEATING_ROUTE_SCHEMA:
        raise ValueError(f"unexpected repeating-route schema: {doc.get('schema')!r}")
    rep = doc.get("repeat") or {}
    legs = [RouteLeg(lg["mode"], lg["to_system"], lg.get("to_body")) for lg in doc["legs"]]
    layovers = [
        LayoverSpec(float(s.get("min_s") or 0.0), float(s.get("max_s") or s.get("min_s") or 0.0))
        for s in (rep.get("layovers") or [])
    ]
    if not legs:
        raise ValueError("a repeating route needs at least one leg")
    if legs[-1].to_system != doc["origin"]["system"] or legs[-1].to_body != doc["origin"]["body"]:
        raise ValueError("a repeating route's last leg must return to its origin")
    cycles = rep.get("cycles")
    if cycles is not None and int(cycles) < 1:
        raise ValueError("a repeating route must run at least one cycle")
    return RepeatingRoute(
        ship=ship_from_transponder(u, doc["ship"]),
        transponder=doc["ship"],
        origin_system=doc["origin"]["system"],
        origin_body=doc["origin"]["body"],
        legs=legs,
        start_at=datetime.fromisoformat(doc["start_at"]),
        layovers=layovers,
        seed=int(rep.get("seed") or 0),
        cycles=None if cycles is None else int(cycles),
        rules=tuple(
            CycleRule(int(r["every"]), int(r["stop"]), float(r["layover_s"]))
            for r in (rep.get("rules") or [])
        ),
    )


def is_repeating(doc: dict) -> bool:
    """Whether a filed document is a repeating route rather than a one-shot."""
    return doc.get("schema") == REPEATING_ROUTE_SCHEMA


# -- Dispatch: one filed document, either schema ---------------------------------


@dataclass(frozen=True)
class ActiveRoute:
    """What a filed document is flying at a queried instant.

    ``cycle`` is 1-based for display (``cycle 3 of 5``) and None for a one-shot
    route; ``cycles`` is the total, or None for a forever loop.
    """

    compiled: CompiledRoute
    cycle: int | None = None
    cycles: int | None = None


def compiled_at(doc: dict, u: Universe, when: datetime) -> ActiveRoute:
    """Compile whatever ``doc`` filed — one-shot, or a repeating route's active cycle.

    The result is **unresolved** (junction queues open-ended) exactly like
    :func:`~hvsim.route.compile_route`, so every caller resolves it the same way.
    """
    if is_repeating(doc):
        rep = from_filed(doc, u)
        cycle, compiled = route_at(rep, when, u)
        return ActiveRoute(compiled, cycle + 1, rep.cycles)
    return ActiveRoute(compile_route(one_shot_from_filed(doc, u), u))


def filed_origin(doc: dict) -> tuple[str, str]:
    """The ``(system, body)`` a filed document departs from, either schema."""
    return doc["origin"]["system"], doc["origin"]["body"]


def fly_filed(
    doc: dict,
    u: Universe,
    *,
    current: Simulation | None = None,
    now: datetime | None = None,
    dev: bool = False,
) -> ActiveRoute:
    """Load a filed document (either schema), enforcing the at-origin precondition.

    Unless ``dev``, a ship with an active plan must be at the new route's origin —
    a navigable point — *now*; re-routing a ship in motion is rejected. See
    :func:`~hvsim.route.fly_filed_route` for the one-shot statement of the rule.
    """
    when = (
        now if now is not None else datetime.fromisoformat(doc.get("start_at") or doc["depart_at"])
    )
    if not dev and current is not None:
        origin = filed_origin(doc)
        loc = current.navigable_location(when)
        if loc != origin:
            raise NotAtOrigin(f"ship is at {loc}, not the route origin {origin}")
    return compiled_at(doc, u, when)
