# ui/ — the Phase 2.5 first-class front-end

A **SvelteKit (Svelte 5) + Canvas-2D** web app for the Honorverse simulator,
consuming the engine API. Vision + stack + the sprint slice are in
[`planning/007`](../planning/007-ui-vision.md).

**Sprint 021 (this):** the **galaxy graph** — placed systems as nodes in the
galactic frame, wormhole links as edges, pan/zoom, click a system → Side Data
Panel, with At-a-glance + legend. The stack-proof slice. Next: system zoom (022),
live ships + Fleet Board (023), junction queue panels (024).

## Layout

- `src/lib/camera.ts` — pure projection/camera (galactic ly ↔ screen px); unit-tested.
- `src/lib/api.ts` — typed engine API client (`/systems`, `/wormholes`, `/junctions`).
- `src/lib/GalaxyMap.svelte` — the Canvas-2D map (nodes, edges, pan/zoom, hit-test).
- `src/lib/{AtAGlance,Legend,DataPanel}.svelte` — the reusable chrome widgets.
- `src/routes/+page.svelte` — composes the map + chrome.

The renderer is deliberately isolated behind the map module so the LOD spine (022)
and a possible future WebGL swap stay localized.

## Develop

```sh
npm install                 # once
just ui-dev                 # Vite dev server; proxies the API to $HVSIM_HOST/$PORT
just ui-build               # -> ui/build (static SPA, base path /ui)
just ui-check               # svelte-check + prettier + vitest (folded into `just check`)
```

## Serve & deploy

Client-only SPA (no SSR), base path `/ui`. The engine serves the built
`ui/build` **same-origin at `/ui`** (`HVSIM_UI_DIST`, or the repo `ui/build` in
dev); the legacy Sol map stays at `/`. `just build` produces a self-contained
image via a multi-stage Dockerfile (a Node stage builds the SPA, copied into the
Python runtime); `just deploy` ships it to kubsdb. Open `http://<host>:<port>/ui`.
