# Grafana / Prometheus wiring (kubsdb)

How the hv-simulator metrics reach Grafana. Source of truth for the homelab
deployment is `~/src/config-src/ansible-k` (roles `prometheus`, `grafana`); this
note captures just what's needed to wire and re-wire the "Ship Status" dashboard.

## Topology

- Shared docker network **`kubsdb-net`** (external bridge). hv-simulator joins it
  (see `deploy/compose.yaml`) so Prometheus can scrape it by name.
- **Prometheus** — container `prometheus`, `http://kubsdb:9090`. Config at
  `/datastore/prometheus/prometheus.yml`; `--web.enable-lifecycle` on.
- **Grafana** — container `grafana`, `http://kubsdb:3000`. Prometheus datasource
  uid is **`prometheus`** (referenced by `ship-status.json`).

## Wire the scrape (direct / v1)

`hvsim` is on `kubsdb-net`, so add a job to the live Prometheus config and reload
(no restart). **Note:** the live file is ansible-templated; a later `ansible
site.yml` overwrites it — the permanent home is the role's `prometheus.yml.j2`
(tracked in kwi).

```yaml
# append under scrape_configs: in /datastore/prometheus/prometheus.yml
  - job_name: "hvsim"
    metrics_path: /metrics
    scrape_interval: "30s"
    static_configs:
      - targets: ["hvsim:8000"]
```

```sh
curl -X POST http://kubsdb:9090/-/reload
curl -s http://kubsdb:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="hvsim")'
```

## Install the dashboard (direct / v1)

Grafana dashboards are **file-provisioned** — no API token. Drop the JSON into the
host dashboards dir; the provider re-scans every 30 s.

```sh
scp grafana/ship-status.json kubsdb:/datastore/grafana/dashboards/ship-status.json
# appears within ~30s at http://kubsdb:3000 (folder: General)
```

ansible copies dashboards with a non-purging `copy`, so this file survives ansible
runs. Permanent home = `ansible-k` `roles/grafana/files/dashboards/` (tracked in kwi).
