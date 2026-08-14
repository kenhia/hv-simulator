# Roadmap

> The general plan for this project. Keep it current; detail lives in the
> sprint records.
>
> Design docs live beside this file (`004-project-plan.md` is authoritative);
> per-sprint records are `../###-<short-name>.md`. Work items and sprint
> proposals are tracked in `korg` under the `hv-simulator` project — the
> `#NNN` references below are korg work-item numbers.

## Now

- **Sprint 038 — kprojects harness** (korg #1236). Put the repo on the shared
  minimal harness: managed instruction block, `sprints/planning|review`,
  `planning/` folded in under `sprints/`. No behaviour change.
- **Next up: repeating routes** (#59, L). Itineraries that auto-file flight
  plans so the galaxy keeps moving without hand-filing every leg. The spec is
  already written — `../035-repeating-routes.md`, deferred out of Sprint 035;
  korg proposal #185.

## Next

Roughly ordered. #59/#64/#67 are bundled as korg proposal #185.

- **#64** (M) Nav planner: precompute the route graph, solving only the
  dynamic last mile. All-pairs hyper edges are recomputed per plan today.
- **#67** (M) In-flight ships shouldn't lose queue position to later filings —
  the wormhole queue resolver re-interleaves the whole active fleet per query.
- **#77** (L) Wormhole termini as distinct entry points/vectors with
  per-terminus queues. Deliberately deferred out of Sprint 037, which landed
  the host-side nexus run-out only; the non-host side still arrives at the
  system, not at a terminus.
- **#476** (M) `/fleet` and `/fleet/ships` recompute the whole fleet resolve on
  every request — cache it.
- **#477** (S) UI live poll runs every 5 s even when the tab is hidden — pause
  or back off on visibility.
- **#66** (M) Expand `nations` data to cover every system's linked nations, and
  teach the scribes to emit it.
- Phase 1.5 leftovers: **M7** live shakedown and **M9** (`kdeskdash` handoff).

## Later / Ideas

- **#58** (M) / **#1018** (XS) Deploy via a registry instead of
  `docker save | ssh docker load`.
- **#60** (S) Fold the hvsim Prometheus scrape + Grafana dashboard into
  `ansible-k` (korg proposal #819). Grafana dashboards are a deferred
  parallel track.
- **#65** (M) Scalable fleet telemetry: a lightweight transponder + vector
  feed, instead of per-ship state queries.
- Controller extras (Phase 2.5): saved routes, non-traditional waypoints, and
  re-routing a ship that is already under way (the at-origin guard blocks it
  today).
- `ALLOW_ANACHRONISMS` enforcement — nation/era hyper-band caps (e.g. Grayson
  pre-Alliance Gamma) are recorded in the dataset but not enforced.
- **Phase 3** — combat, LLM narrative, and admiral agents, as separate
  services. The engine gains only new *segment kinds*; route planning and
  worldgen stay outside the physics box.
