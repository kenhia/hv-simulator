# Sprint 007 — Deploy to kubsdb (Phase 1.5 / M6)

Implements milestone **M6** from `planning/004-project-plan.md` (Phase 1.5 —
Operate & Observe). First real deployment: the simulator runs as a persistent
service on `kubsdb`, in real time, managed from a root `justfile`.

## Goal

`just deploy` builds the image, ships it to `kubsdb`, and brings the service up
reachable at `http://kubsdb:4667` — real-time clock, persistent SQLite, restarts
on reboot. `just health` confirms it from kai. This unblocks M7 (live shakedown)
and M8 (metrics/Grafana), which need a live target to point at.

## Decisions (baked in — flag on review)

- **Image delivery: build on kai, `docker save | ssh kubsdb docker load`.** No
  registry, no extra auth; simplest homelab path. A registry (ghcr) move is
  deferred to its own future sprint — tracked as **kwi #58**.
- **No `up` recipe (YAGNI).** `deploy` ends in `compose up -d`, so it *is* the
  idempotent "up"; `down` + `deploy` covers a clean restart. Add a no-transfer
  restart later only if it's actually wanted.
- **Orchestration on kubsdb: a dedicated deploy compose** (`deploy/compose.yaml`)
  with `image:` (not `build:`), `restart: unless-stopped`, a named volume, and
  env — distinct from the repo-root `docker-compose.yml` (which builds locally
  for dev). Declarative and survives host reboots.
- **Real time, clock locked.** `HVSIM_DEV_CLOCK` unset on the deployed instance —
  production pacing is the point; `PUT /clock` returns 403 there.
- **Persistent SQLite** on a named volume (survives restart and redeploy).
- **Port 4667** (confirmed free on kubsdb in the homelab port audit).

## Scope

- A root **`justfile`** with recipes:
  - `build` — build the image, tagged `hvsim:<version>-<git-sha>` (+ `:latest`).
  - `deploy` — build → `save | ssh load` → copy `deploy/compose.yaml` → `ssh
    kubsdb docker compose up -d` → wait for healthy.
  - `health` — `curl http://kubsdb:4667/health` (and `/clock`).
  - `logs` — `ssh kubsdb docker compose logs -f` (tail).
  - `down` — stop/remove the deployed stack (volume preserved).
  - `seed` — file 2-3 demo ships against the deployed instance (used by M7).
    Ships are named **`XSS <name>`** (X = experimental, so R&D ships are obvious
    in the fleet) with a spread of accelerations — ~**100 g** (massive in-system
    transport) up to ~**700 g** (tiny courier boats trading size/safety for raw
    speed).
- **`deploy/compose.yaml`** — the kubsdb stack (image, port, volume, restart,
  healthcheck, real-time env).
- **README "Deploying" section** documenting `just deploy` / `just health`.
- **kubsdb reachability**: verify `ufw` state on kubsdb; open 4667 only if a
  firewall is actually active (as on kai, it may be inactive — check, don't
  assume).

## Out of scope

- **ghcr / registry pipeline** (noted as the alternative; not built unless chosen).
- **CI/CD**, TLS/reverse proxy, auth, multi-host — later if ever.
- **Live observation / completed-trip watching** — that's M7.
- **Prometheus `/metrics` + Grafana** — M8.
- **Postgres** — stays SQLite until Phase 2.
- Any change to the simulator's behavior; this sprint is packaging/ops. If a
  small code tweak is needed (e.g. a config knob), keep it minimal and tested.

## Tasks

- [x] Ensure `just` is available on kai (document the install if not); pick the
      image tag scheme (version + git short sha).
- [x] Author the root `justfile` (recipes above; variables for HOST=`kubsdb`,
      PORT=`4667`, IMAGE).
- [x] Author `deploy/compose.yaml` (image, `4667:8000`, named volume,
      `restart: unless-stopped`, healthcheck, no dev clock).
- [x] `just deploy` to kubsdb; check `ufw` and open 4667 if active.
- [x] `just health` from kai returns ok; run the canonical Earth→Titan→Earth
      flow over the LAN against kubsdb.
- [x] Confirm persistence: restart the container on kubsdb, verify the ship/plan
      and queryable state survive.
- [x] README "Deploying" section.

## Acceptance criteria

- `just deploy` builds, transfers, and starts the service on kubsdb with no
  manual steps; `just health` (from kai) returns `{"status":"ok"}` against
  `http://kubsdb:4667/health`.
- The canonical run (create ship → file Earth→Titan Station (6h)→Earth → query
  state) works over the LAN against the deployed instance.
- The deployed instance runs **real time** (rate 1.0) and `PUT /clock` returns
  **403** (dev controls off).
- Flight plans **persist across a container restart** on kubsdb (named volume),
  with state queryable without recompilation.
- `restart: unless-stopped` is set so the service comes back after a host reboot
  (policy verified; full reboot test optional).
- Local validation gate stays green (`uv run pytest`, `ruff check`,
  `ruff format --check`).

## Notes / decisions

- Mostly ops/scripts — expect little or no Python change, so `main` stays green
  throughout.
- `ssh kubsdb` already works passwordless (used it for the homelab port audit),
  so `deploy`/`logs`/`health` can shell over SSH directly.
- The deploy compose deliberately omits `HVSIM_DEV_CLOCK`. If we ever want a
  staging instance with fast-forward, that's a separate compose/profile.
- Image transfer size: the `python:3.13-slim`-based image is modest; `save|ssh
  load` per deploy is fine at homelab scale. Revisit ghcr (**kwi #58**) if deploys
  get frequent or go multi-host.
- Seed ships file ordinary one-shot flight plans for now. The richer "ships live
  on a repeating route" idea (auto-refiling, randomized layovers, crew-change
  cycles) is captured as **kwi #59** for a future sprint.

## Outcome — DONE

- Shipped on branch `sprint-007-deploy-kubsdb`. Deployed and verified live on
  **kubsdb**; no Python change, so the suite is unchanged (61 tests) and
  `just check` is green (tests + ruff + format).
- New files: root `justfile` (build/deploy/health/logs/down/seed/check),
  `deploy/compose.yaml` (image:, real-time, named volume, `restart:
  unless-stopped`, healthcheck), `deploy/seed.sh` (XSS ships, 100-700 g).
- `just deploy` works end to end: build on kai -> `docker save | ssh kubsdb
  docker load` -> scp compose -> `compose up -d` -> health ok. Tooling present:
  `just` 1.50 on kai, docker compose v5 on kubsdb; 4667 free; both hosts' `ufw`
  inactive (no firewall change needed).
- Verified: `just health` ok; canonical Earth->Titan Station(6h)->Earth over the
  LAN (1d 9h 7m); `PUT /clock` -> **403** (dev off, rate 1.0); flight plans +
  state **persist across a container restart** (named volume, no recompile).
- Decisions recorded: ghcr deferred (**kwi #58**); no `up` recipe (deploy is the
  idempotent up); routes deferred (**kwi #59**).
- Live instance currently carries the 3 seeded XSS ships + an XSS Harrington
  canonical run — fodder for M7 (live shakedown / watch trips complete).
