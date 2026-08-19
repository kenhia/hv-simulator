"""The precomputed route topology — built once per artifact, cached per speed class.

Route-finding asks the same static question over and over: *which systems, by
which mode*. The universe's shape — which systems are placed, how far apart they
are, which pairs a wormhole links — never changes once an artifact is loaded, so
:class:`RouteGraph` reads it **once** and every later search walks memory (#64).

The dynamic half stays dynamic. A hyper edge's weight is

    dist_ly * k + HYPER_LEG_OVERHEAD_S      k = T_year / (band_multiplier * cruise_c)

so ``k`` — one scalar per ship **speed class** — is the only ship-dependent term,
and the Dijkstra predecessor table caches per ``(k, origin)``. Two ships with the
same band and cruise velocity share a table; a faster ship gets its own. The real
clock is still solved per request by :func:`~hvsim.route.compile_route` against
live body positions: this precomputes the *topology*, not the itinerary.

Caches are keyed weakly by ``Universe`` instance and hold pure functions of an
immutable artifact, so a benign race across FastAPI's threadpool can only
recompute the same answer.
"""

from __future__ import annotations

import heapq
import math
import threading
import weakref
from dataclasses import dataclass, field

from hvsim.universe import Universe

HYPER, WORMHOLE = "hyper", "wormhole"
# A flat per-hyper-leg n-space allowance (run-out + approach) so the search
# slightly prefers fewer hyper hops; the engine computes the real overhead.
HYPER_LEG_OVERHEAD_S = 6 * 3600.0


@dataclass(frozen=True)
class RouteGraph:
    """The static navigable topology of one artifact.

    ``systems`` are the *placed* ones (a system without galactic coordinates
    cannot be routed to). ``distance_ly`` is precomputed all-pairs;
    ``wormhole_adj`` holds only true junction links (``transit == "instant"`` —
    the link table also carries hyper_leg/transfer annotations that are not
    wormholes).
    """

    systems: tuple[str, ...]
    wormhole_adj: dict[str, tuple[str, ...]]
    buffer_s: float
    _dist: dict[tuple[str, str], float] = field(repr=False, default_factory=dict)
    # (k, origin) -> node -> (from_node, mode); filled lazily, see routing_table().
    _tables: dict[tuple[float, str], dict[str, tuple[str, str]]] = field(
        repr=False, default_factory=dict
    )
    _lock: threading.Lock = field(repr=False, default_factory=threading.Lock, compare=False)

    def distance_ly(self, a: str, b: str) -> float | None:
        """Precomputed galactic-frame distance between two placed systems."""
        return self._dist.get((a, b))


def build(u: Universe) -> RouteGraph:
    """Read the artifact's navigable topology into a :class:`RouteGraph`."""
    coords = {}
    for s in u.systems():
        c = u.coordinates(s["id"])
        if c is not None:
            coords[s["id"]] = c
    systems = tuple(sorted(coords))

    dist: dict[tuple[str, str], float] = {}
    for i, a in enumerate(systems):
        for b in systems[i + 1 :]:
            d = math.dist(coords[a], coords[b])
            dist[(a, b)] = dist[(b, a)] = d

    adj: dict[str, set[str]] = {}
    for link in u.wormhole_links():
        a, b = link.get("from_system_id"), link.get("to_system_id")
        if a and b and link.get("transit") == "instant":
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

    return RouteGraph(
        systems=systems,
        wormhole_adj={k: tuple(sorted(v)) for k, v in adj.items()},
        buffer_s=(u.transit_model() or {}).get("buffer_normal_s") or 0.0,
        _dist=dist,
    )


_graphs: weakref.WeakKeyDictionary[Universe, RouteGraph] = weakref.WeakKeyDictionary()
_graphs_lock = threading.Lock()


def route_graph(u: Universe) -> RouteGraph:
    """The artifact's :class:`RouteGraph`, built on first use and cached."""
    graph = _graphs.get(u)
    if graph is None:
        graph = build(u)
        with _graphs_lock:
            _graphs[u] = graph
    return graph


def routing_table(graph: RouteGraph, k: float, origin: str) -> dict[str, tuple[str, str]]:
    """Dijkstra predecessors from ``origin`` for a ship of speed class ``k``.

    ``node -> (from_node, mode)`` covering every system reachable from ``origin``;
    cached, so the second search for the same speed class is a dict lookup.
    """
    key = (round(k, 6), origin)
    table = graph._tables.get(key)
    if table is not None:
        return table

    dist = {origin: 0.0}
    prev: dict[str, tuple[str, str]] = {}
    pq: list[tuple[float, str]] = [(0.0, origin)]
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist.get(node, math.inf):
            continue
        edges: list[tuple[str, str, float]] = [
            (nb, WORMHOLE, graph.buffer_s) for nb in graph.wormhole_adj.get(node, ())
        ]
        for nb in graph.systems:  # hyper edges (all pairs)
            if nb != node:
                edges.append((nb, HYPER, (graph.distance_ly(node, nb) or 0.0) * k))
        for nb, mode, w in edges:
            nd = d + w + (HYPER_LEG_OVERHEAD_S if mode == HYPER else 0.0)
            if nd < dist.get(nb, math.inf):
                dist[nb] = nd
                prev[nb] = (node, mode)
                heapq.heappush(pq, (nd, nb))

    with graph._lock:
        graph._tables[key] = prev
    return prev


def hops(graph: RouteGraph, k: float, origin: str, dest: str) -> list[tuple[str, str]]:
    """Min-time hops origin->dest as ``(mode, to_system)``; raises if unreachable."""
    for sysid in (origin, dest):
        if sysid not in graph.systems:
            raise ValueError(f"system {sysid!r} is not placed (no coordinates)")
    prev = routing_table(graph, k, origin)
    if dest not in prev and dest != origin:
        raise ValueError(f"no route from {origin!r} to {dest!r}")
    out: list[tuple[str, str]] = []
    node = dest
    while node != origin:
        frm, mode = prev[node]
        out.append((mode, node))
        node = frm
    out.reverse()
    return out
