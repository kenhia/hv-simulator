# Sprint 040 — deploy via the registry, cache the fleet resolve, pause the hidden poll

A backlog-drain sweep, not a feature sprint: korg proposal **#2222**, slice 11
of program **#2233** ("the sub-1000 sweep"). Four work items, three of them
older than a month, in three unrelated corners of the repo — the deploy path,
the `/fleet` read path, and the UI's poll loop.

Covered: **#58** + **#1018** (one ask, two filings), **#476**, **#477**.

## Premise check (the program's standing rule: verify before you work)

| Item | Verdict |
|---|---|
| #58 deploy via ghcr | **drifted** — the ask holds (`justfile` still had `docker save \| ssh docker load`) but its *target* was superseded. |
| #1018 deploy via the homelab registry | **holds**, and the pattern was already settled — korg #1011 shipped it. |
| #476 `/fleet` recompiles per request | **holds** — `resolved_fleet` ran the whole compile+fold on every call. |
| #477 UI polls while hidden | **holds** — three `setInterval`s, no `visibilitychange` listener anywhere in `ui/`. |

**#58 asked for the wrong registry, and that is the interesting part.** It was
filed 2026-06-13 proposing `ghcr.io/kenhia/hv-simulator` with a `write:packages`
PAT on both hosts. Two months later k-homelab sprint 020 stood up the homelab
package store, and `docs/deploying.md` became doctrine: images go to
`kubsdb.encke-wahoo.ts.net:5000`, TLS from `tailscale serve`, nothing to log in
to. #1018 is that same ask re-filed against the doctrine. So the two items were
closed on one change — built to #1018's target, which is also the one that
needs no credential.

## What shipped

### The deploy path (#58, #1018)

`docker save | ssh docker load` → tag, push, pull. The shape is copied from
korg's `deploy-kubsdb` skill rather than invented, because #1018 said to and
because the failure modes there are already paid for:

- **The version is the 12-char git short SHA.** `engine/pyproject.toml` carries
  a flat `0.1.0` that is not maintained per release, so a semver tag would
  collide on every build and name nothing.
- **Both tags, SHA first.** `:latest` alone recreates the no-history status quo
  the registry exists to fix. Pushing the SHA first means a failed `:latest`
  push leaves a complete, named build with `:latest` still on the last good one.
- **A dirty tree refuses to deploy.** The image carries
  `org.opencontainers.image.revision`, and a build labelled with a commit it is
  not is a build nothing can roll back to.
- **The revision assertion is part of the deploy, not the verify.**
  `docker compose pull` prints the same thing whether it fetched anything or
  matched a cache, so its output is not evidence. `deploy/remote-up.sh` asserts
  the running container's image reference *and* its revision label, and fails
  the deploy if either disagrees.
- **The exact build is pinned on the host.** `remote-up.sh` writes
  `HVSIM_IMAGE=<ref>` to the compose project's `.env`, so a later hand-run
  `docker compose up -d` on kubsdb resolves the same image instead of drifting
  to whatever `:latest` has become.

New: `just rollback <tag>` (pin any build still in the registry, no rebuild) and
`just image-tags` (list the candidates) — the payoff #1018 asked for, and the
thing `docker save` never had.

The remote half is a script (`deploy/remote-up.sh`) rather than an inline
`ssh` heredoc, matching the existing `deploy/*.sh` and sidestepping kubsdb's
fish login shell, which mis-parses `$()`.

### The fleet resolve is memoized (#476)

`resolved_fleet` compiled every filed route from scratch and re-folded the
junction calendar on **every request** — and the deployed dashboard polls
`/fleet` every 5 s per open client. The compile+fold is a pure function of the
active route-set, so it is now memoized on `app.state`, fingerprinted by that
route-set (row id + `created_at` + the filed doc). Filing or aborting a route
changes the fingerprint; that is the whole invalidation story.

Measured on the real 40-ship artifact, all flying repeating routes:

| | before | after |
|---|---|---|
| `GET /fleet` | 56.9 ms | **11.4 ms** |
| `GET /fleet/ships` | 47.6 ms | **1.9 ms** |

**The subtlety that makes it correct.** The work item predates Sprint 039 and
says the resolve is "deterministic for a given active route-set — only
`state(when)` depends on the query time". That stopped being true when
repeating routes landed: `compiled_at` picks *the cycle covering `when`*, so a
memo with no time bound would serve cycle 1 for the rest of a ship's life. So
`ActiveRoute` now carries the active cycle's `valid_from`/`valid_until` (new
`repeat.cycle_window`, reading boundaries the walk already memoizes), the memo
holds only over the intersection of those windows, and a one-shot route — whose
compilation genuinely does not depend on `when` — contributes no bound at all.
`test_the_memo_does_not_outlive_a_repeating_cycle` fails without it.

This is a memo of a pure function, **not** a background tick: the no-loop,
zero-drift discipline is untouched, and the per-ship `state(when)` evaluation
still runs per request, closed-form.

### The UI poll pauses when nobody is looking (#477)

`LiveFleet` polled `/fleet` + `/fleet/{tp}/state` every 5 s for as long as the
page was loaded, visible or not — the observed 2026-07-18 CPU spike on kubsdb
was a backgrounded client doing exactly that. It now tears the timers down on
`visibilitychange` → hidden and rebuilds them on the way back, with an immediate
refresh so the board is current the moment it is looked at again. Dead reckoning
means a hidden tab loses nothing by skipping the polls.

The pause point is `live.setHidden(hidden)`, public and driven by the listener,
because the UI test environment is `node` with no DOM — the tests drive it
directly rather than the suite gaining jsdom.

## Decisions

- **`/fleet/ships` did not get the second cache the work item proposed.** #476
  suggested also caching `navigable_location` per ship on a coarse time bucket.
  Measured, the shared resolve *was* the whole cost (47.6 ms → 1.9 ms once it
  was memoized); the remaining 1.9 ms is the per-ship phase derivation. A time
  bucket would have traded a stale phase in the Flight Planner's picker for
  about two milliseconds.
- **The memo is per-process, in-memory, and dies with the app.** No TTL and no
  eviction: it holds exactly one entry, replaced whenever the route-set or the
  cycle window moves. A second worker would keep its own, which is correct
  because the value is a pure function of shared inputs.
- **The lock is for the thundering herd, not for safety.** `_FleetResolve` is
  frozen and published whole; the lock exists so N concurrent pollers arriving
  on a cold memo produce one compute instead of N.
- **`.env.example` gained `HVSIM_REGISTRY`.** The registry is parameterised the
  same way the host and port already were, rather than hardcoded to kubsdb.

## Verified

- `just check` green: 185 engine tests (9 new), ruff clean, tools, 68 UI tests
  (2 new).
- The registry path proven end to end from this machine: `docker push` of a
  real SHA-tagged build succeeds over the tailnet, and the tag is readable back
  out of the registry — see the sprint's korg handoff for the tag.

## Follow-ups

- **The live cutover was deliberately not run.** `just deploy` now ends in
  `docker compose up -d` on kubsdb, and running it from the sprint branch would
  have put unreviewed code on the live service ahead of the ship gate. The first
  registry deploy is a post-merge action. Filed as a work item.
- apt-temps **#1019** is the same conversion for a sibling repo and is
  untouched here; its shape comes from korg #1011, same as this one.
