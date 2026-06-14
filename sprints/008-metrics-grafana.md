# Sprint 008 — Prometheus /metrics + Grafana "Ship Status" (Phase 1.5 / M8)

Implements milestone **M8** from `planning/004-project-plan.md`. Makes the live
deployment observable: a Prometheus `/metrics` endpoint on the API, scraped by
the existing Prometheus on `kubsdb`, surfaced in a Grafana "Ship Status"
dashboard.

## Goal

`GET /metrics` exposes ship telemetry in Prometheus format; the kubsdb Prometheus
scrapes it every 30 s; a Grafana dashboard shows the fleet (table + time-series)
from real data. The scrape **computes current state analytically** — no
background loop, faithful to the project's design.

## Decisions

- **Pull, not push** (project-wide): `prometheus_client` exposes `/metrics`; a
  scrape triggers a `state_at`-style eval for every ship. No tick.
- **Wiring: direct for v1** (chosen this session). Apply the scrape job + import
  the dashboard straight to live Prometheus/Grafana so it's live now; commit the
  dashboard JSON + scrape snippet + a deployment-facts reference in-repo; fold
  into `ansible-k` IaC later (tracked as a kwi item created in this sprint).
- **30 s scrape** (positions change over hours; finer is wasteful).
- **Grafana/Prometheus deployment facts** captured as a durable `reference`
  memory (+ a short `grafana/` note) so future work doesn't re-read ansible-k.

## Scope

- **`/metrics` endpoint** (`prometheus_client`), computed on scrape:
  - `hvsim_ship_speed_fraction_c{ship_id,name}`
  - `hvsim_ship_speed_km_s{ship_id,name}`
  - `hvsim_ship_percent_complete{ship_id,name}`
  - `hvsim_ship_distance_to_destination_km{ship_id,name}`
  - `hvsim_ship_eta_seconds{ship_id,name}` (seconds until arrival; 0 if idle/arrived)
  - `hvsim_ship_info{ship_id,name,phase,destination}` = 1 (slowly-changing state)
  - `hvsim_ships{phase}` (count by phase), `hvsim_bodies_total`
  - `hvsim_clock_rate`, `hvsim_sim_time_seconds` (unix sim time)
- **ansible-k reference extraction**: Prometheus scrape-config location + reload
  method; Grafana base URL; Prometheus datasource name/uid; dashboard
  provisioning method; API auth. → `reference` memory + `grafana/DEPLOY.md`.
- **Prometheus**: add a scrape job for the deployed sim — preferably targeting
  `hvsim:8000/metrics` over the shared `kubsdb-net` (see network note), with the
  published `kubsdb:4667/metrics` as fallback — reload, confirm the target is UP.
- **Grafana "Ship Status" dashboard** (JSON committed at `grafana/ship-status.json`):
  a ships table (name, phase, speed c, %-complete, ETA, distance) + time-series
  (speed, distance-remaining). Imported to the live Grafana.
- **README**: note `/metrics` and the dashboard.

## Out of scope

- **ansible-k IaC integration** — deferred; tracked as a kwi item this sprint.
- Alerting / alert rules; SLOs.
- Auth on `/metrics` (open on the LAN, like the rest of the API).
- Push / pushgateway (declined project-wide).
- `kdeskdash` text mode — that's M9.

## Tasks

- [ ] Add `prometheus_client`; implement `GET /metrics` (build a fresh registry
      per scrape from current ship state; no module-global mutation; no loop).
- [ ] Tests: `/metrics` returns 200 `text/plain` with the metric names; with a
      seeded ship, its labelled series are present and numeric.
- [ ] Extract ansible-k Prometheus/Grafana facts → `reference` memory +
      `grafana/DEPLOY.md`. (Will surface the Grafana auth needed for import — may
      need a service-account token; ask at that point if so.)
- [ ] `just deploy` to push the `/metrics` build live on kubsdb.
- [ ] Add the Prometheus scrape job (30 s) + reload; verify target UP.
- [ ] Build + import the Grafana "Ship Status" dashboard; verify panels populate
      from the live fleet; commit `grafana/ship-status.json`.
- [ ] Create the kwi item: "fold hvsim scrape + dashboard into ansible-k".
- [ ] README note; gate green.

## Acceptance criteria

- `GET /metrics` on the deployed sim returns Prometheus exposition with the
  per-ship gauges, the phase info-metric, and counts; a scrape reflects current
  state (e.g. a mid-transit ship shows non-zero speed) with no background loop.
- Prometheus on kubsdb lists the hvsim target **UP**, scraping at 30 s.
- The Grafana **"Ship Status"** dashboard renders the live fleet — table rows
  per ship and time-series that move as ships progress.
- `grafana/ship-status.json` + the Prometheus scrape snippet + the deployment
  reference are committed; the ansible-k follow-up is filed in kwi.
- `/metrics` has tests; local gate (`just check`) stays green.

## Notes / decisions

- Label cardinality is fine for a small fleet (ship_id+name). If ships grow large
  in number, revisit (drop name from numeric series, keep it on `*_info`).
- The endpoint reuses the same state path as `/ships`; arrived/idle ships emit
  sensible zeros rather than vanishing.
- Network (decide at wiring time, leaning toward `kubsdb-net`): kubsdb has an
  established external bridge **`kubsdb-net`** that Prometheus/Grafana already
  use (per the Grafana spec in `ansible-k`: "Network: `kubsdb-net` (external
  bridge, already exists)"). **Preferred:** join hvsim to `kubsdb-net` so
  Prometheus scrapes `hvsim:8000/metrics` by container name — no dependence on
  the published host port. This adds an `external: true` network to
  `deploy/compose.yaml` (a small change to the M6 file). **Fallback:** scrape the
  host-published `kubsdb:4667/metrics` (bound on 0.0.0.0), no compose change.
- Touching live Prometheus/Grafana is an outward action on the homelab; the
  reference-extraction step happens first so the wiring is done knowingly.

## Outcome — DONE

- Shipped on branch `sprint-008-metrics-grafana`. 63 tests pass (2 new metrics
  tests); `just check` green.
- `/metrics` (`prometheus_client`) renders a fresh registry per scrape from
  current ship state — no loop. Module `hvsim/api/metrics.py`; route in `app.py`.
- **Wired live on kubsdb (direct/v1):** hvsim joined `kubsdb-net`
  (`deploy/compose.yaml`); redeployed via `just deploy`. Prometheus scrape job
  `hvsim -> hvsim:8000/metrics` @30s added to the live config + reloaded
  (`/-/reload`); target verified **UP** and queryable. Grafana **"Ship Status"**
  dashboard (`grafana/ship-status.json`) dropped into the file-provisioned
  dashboards dir; confirmed provisioned in `grafana.db` (uid `hvsim-ship-status`,
  no errors).
- **No Grafana token needed** — dashboards are file-provisioned; datasource uid
  is the stable `prometheus`. Facts captured in `grafana/DEPLOY.md` + the
  `kubsdb-observability` agent memory.
- Follow-up (fold scrape + dashboard into ansible-k) tracked as **kwi #60**.
  Caveat recorded there: the live Prometheus scrape edit is overwritten by the
  next `ansible site.yml` until folded in; the Grafana dashboard survives.
- Visual polish of the dashboard left to the eye (Grafana `allowUiUpdates: true`);
  it loads with valid panels and live data.
