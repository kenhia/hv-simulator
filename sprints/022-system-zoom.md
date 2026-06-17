# Sprint 022 — System zoom (the LOD spine)

The technically defining Phase 2.5 sprint: descend from the galaxy graph into a
**per-system top-down** — the Sol-map POC, generalized to any system — with the
breadcrumb that grows on the way down. This is the level-of-detail (LOD) spine the
whole UI hangs on; 023 (live ships) and 024 (queue panels) ride on it.

Vision: [`planning/007`](../planning/007-ui-vision.md). Builds on 021's galaxy graph
+ camera/renderer modules.

## Goal

Zoom into a system node and the view **becomes** that system's heliocentric
top-down: star(s) at center, planets (and moons) at **live positions**, the
**hyper-limit ring**, stations, and a junction-nexus marker. The At-a-glance
breadcrumb tracks depth: `Galaxy → Sol → Sol / Earth`. A **zone mode** centers +
zoom-clamps on one system. Zoom back out returns to the galaxy graph.

## The key design decision (please weigh in)

The vision calls for "one continuous zoom." The galaxy frame is **light-years** and
a system is **AU/km** — ~5 orders of magnitude apart — so a single literal camera
is awkward (a system is a sub-pixel point until absurd zoom). Proposed pragmatic
approach, presented *as* continuous:

- **Two scenes, one shell, threshold + animated transition.** Galaxy scene
  (021's graph) and a System scene (heliocentric). Zooming a system node past a
  scale threshold (or **double-clicking** it) **animates** a zoom-in and swaps to
  the System scene centered on it; zooming out past a threshold animates back.
  **Single click stays "select + show the data panel"** (021's behaviour); double
  click is the mouse way *in*. Shared camera module, shared chrome, shared
  breadcrumb — so it *feels* continuous.

Alternative (deferred): a single log-scale camera spanning ly→AU. More "pure" but
much fiddlier; not worth it for v1. **Decision needed before building** — default
is the two-scene transition.

## Design

### Scenes & transition
- A `scene` state: `galaxy` | `system(id)`. The Galaxy scene is 021's GalaxyMap.
  The System scene is a new heliocentric renderer reusing the camera module
  (world units = AU; star at origin).
- Enter: **double-click** a node, **Enter** key on the selected node, or zoom in
  past a threshold over a node → animate camera to the node, cross-fade to the
  System scene. Exit: **Esc**, or zoom out past a threshold → animate back to the
  node's galaxy position. (Single click selects + opens the panel, unchanged.)

### Keybindings — reserve now, implement incrementally
The full shortcut scheme is deferred, but we **reserve the map as we go** so later
sprints don't collide. **Avoid the browser-captured function keys** (F1 help, F3
find, F5 reload, F6, F11 fullscreen, F12 devtools) and most `Ctrl/Cmd` combos —
prefer plain single keys while the map has focus. Reserved (★ = implemented in 022):

| Key | Action | Sprint |
|-----|--------|--------|
| `Enter` ★ | enter the selected system (drill in) | 022 |
| `Esc` ★ | exit System scene / dismiss panel (back out) | 022 |
| `z` ★ | toggle zone mode (center + clamp) | 022 |
| `f` ★ | fit / reset view (frame all) | 022 |
| `/` | focus Locate-a-ship search | 023 |
| `l` | layer toggles (ships, labels, …) | 023/025 |
| `m` | main menu (Observer/Controller); right-click held in reserve too | 025 |
| `Space` | play/pause the dev time scrubber | 025 |
| `,` `.` | step the dev clock back / forward | 025 |

Keep the binding table in the UI (a small `keymap` module) so it's the single
source of truth and a future "?" overlay can render it.

### System scene (the generalized Sol map)
- **Star(s)** at center (binary: two stars offset by the artifact's separation;
  simplify to a single marker if separation data isn't surfaced yet).
- **Planets + moons** at live positions from `GET /systems/{id}/bodies?at=now`,
  polled; moons drawn when zoomed to their planet. Orbital motion is slow — poll +
  redraw (no dead-reckoning v1; that lands with ships in 023).
- **Hyper-limit ring** — the primary star's limit (needs API; see below).
- **Stations / nexus** — places (needs API). Stations ride on their parent body;
  the junction nexus gets a marker (canon in-system position is uncharted — place
  it at the canon radial distance, fabricated bearing).
- Click any object → the existing Side Data Panel (extended for bodies/places).

### Breadcrumb + zones
- At-a-glance breadcrumb: `Galaxy` (galaxy scene) → `<System>` (system scene) →
  `<System> / <Body>` (a body selected/focused). Plus per-system counts.
- **Zone mode** — a hotkey centers the System scene on the current system and
  **clamps pan/zoom** to a sensible bound (e.g. out to ~the outer system / hyper
  limit). Toggle off to resume free zoom.

### Engine/API additions (the new data the view needs)
- **`GET /systems/{system_id}`** (single-system detail; declared in the contract):
  add **primary `hyper_limit_lmin`** + `stars` (role, spectral type) + binary
  separation, so the UI can draw the limit ring and star(s).
- **`GET /systems/{system_id}/places`** — stations/forts/nexus with positions
  (ride-on-body → parent body position; nexus → canon radial distance). New
  `Universe.places` accessor + a `places` table read.
- Both 404 on unknown system, 503/empty without the artifact. Update
  `engine-openapi.yaml`.

## Scope

1. System scene: heliocentric renderer (star, planets, moons, hyper-limit ring),
   reusing the camera module (AU units).
2. Galaxy↔system **scene transition** (threshold + animation), shared shell.
3. Breadcrumb (galaxy → system → body) + per-system counts in At-a-glance.
4. Zone mode (center + clamp) on a hotkey.
5. Side Data Panel extended for bodies + places.
6. Engine: `GET /systems/{id}` (hyper limit + stars) and `GET /systems/{id}/places`;
   `Universe.places`; OpenAPI updated.
7. Tests: Vitest for any new pure logic (scene threshold, AU projection, breadcrumb
   derivation); engine tests for the two new endpoints (404 + shape).

## Out of scope (later)

- **Live ships in-system** + dead-reckoning + Fleet Board — 023.
- **Junction queue panels** — 024 (needs 020's endpoint, already built).
- **Region/zone *clustering*** for crowded areas (collapse many close objects into
  an expandable marker) — a later refinement; note where it would slot.
- **3D galaxy-model viewer** — later.
- **Faction colors, main menu, dev time controls, detail timelines** — 025.

## Tasks

- [ ] Decide the zoom approach (two-scene transition vs single log camera);
      default two-scene.
- [ ] Engine: `GET /systems/{id}` (+ hyper limit, stars, binary) and
      `GET /systems/{id}/places` (+ `Universe.places`); schemas + OpenAPI; tests.
- [ ] System scene renderer (star/planets/moons/hyper-limit ring/stations/nexus),
      AU camera; click→panel.
- [ ] Galaxy↔system transition (threshold + animation); scene state in the shell.
      Entry via double-click / `Enter` / zoom-in; exit via `Esc` / zoom-out
      (single-click still = select + panel).
- [ ] `keymap` module (single source of truth); wire the 022 keys (`Enter`/`Esc`/
      `z`/`f`); reserve the rest (table above) — avoid browser-captured function keys.
- [ ] Breadcrumb + per-system counts; zone mode (center + clamp) on `z`.
- [ ] Side Data Panel: bodies + places.
- [ ] Vitest (scene/projection/breadcrumb) + engine endpoint tests; `just check` +
      `just contracts` green.
- [ ] Deploy to kubsdb + demo; CLAUDE.md + `planning/007` (mark 022 landed) updated.

## Acceptance criteria

- **Double-clicking** (or zooming into, or `Enter` on) a system enters its
  heliocentric top-down (star, planets at live positions, hyper-limit ring,
  stations, nexus); `Esc`/zoom-out returns to the galaxy graph — feels continuous
  (animated). Single click still just selects + opens the panel.
- The 022 keys (`Enter`/`Esc`/`z`/`f`) work and live in a `keymap` module; the
  deferred keys are reserved (documented), not bound.
- The breadcrumb reads `Galaxy → <System> → <System> / <Body>` as you descend;
  zone mode centers + clamps on a system.
- `GET /systems/{id}` exposes the hyper limit + stars; `GET /systems/{id}/places`
  returns stations/nexus; both 404 on unknown system.
- `just check` (engine + UI) + `just contracts` green; deployed + demoed.

## Notes / decisions

- **The hard part is the LOD spine**, not any one view — keep the scene/transition
  logic clean and the renderers behind module boundaries (021's discipline), so
  023 can drop ships onto either scene.
- **Sol is the proof**: its top-down already exists (the legacy `/` map). Generalize
  it; when the System scene covers Sol, the legacy map can be retired (later).
- The nexus/station in-system positions are largely **fabricated** (canon gives
  radial distance, not bearing) — flag `canon:false` like the galactic frame.
