# Sprint 032 — Board filter + at-planet ship labels

Two demo-polish UI tweaks (no engine changes). Repeating routes → 033.

Plan: [`planning/007`](../planning/007-ui-vision.md). All in `ui/`.

## Goal

- **Fleet Board filter** — declutter the roster: a **hide-arrived** toggle plus a
  **per-nation** filter (checkboxes by nation, shown by name).
- **At-planet ship labels** — when ships sit at rest at a body, draw a leader line
  from the body's label listing their transponder codes (stacked), instead of
  overlapping dots on the planet.

## Part 1 — Fleet Board filter (UI)

A compact **filter control** in the board header (next to the search), opening a
small popover:
- **Hide arrived** checkbox — excludes ships whose phase is `arrived` (finished
  flight plan, at rest at their destination).
- **Nations** — a checkbox per nation present in the roster; unchecking hides that
  nation's ships. Default: all on. Nation derived from `transponder.split('.')[0]`;
  shown by **name** via a small `nation.ts` code→name map (Sol, Manticore, Grayson,
  Beowulf, Haven, Solarian League, Erewhon, Andermani, Silesia, Masada, …) with the
  code as a fallback for unknowns.
- Pure filtering of the existing `roster` (FleetEntry[]); a small tested
  `boardFilter(roster, {hideArrived, nations})` helper keeps it out of the
  component. The search box still applies on top.
- Show the active filter state subtly (e.g. a dot on the filter button when any
  filter is on) so it's clear ships are hidden.

## Part 2 — At-planet ship labels (SystemMap, UI)

When one or more tracked ships are **at rest at a body** (phase `arrived` /
`layover` / `predeparture`, in this system, heliocentric), replace their individual
dots with a **leader line off the body's label**:

```text
  ● Medusa
     | 213.2.1
     | 213.2.3
```

- **Grouping:** match each at-rest ship to the body it sits on by nearest body
  position (at rest the engine returns the exact body position, so the match is
  clean; use a small screen-space tolerance). Skip ships in motion / `queued` /
  `wormhole_transit` (those keep their current rendering — dot+vector, or the nexus
  placement for queued).
- **Render:** from a point a **small indent right of the body dot, just left of
  centre under the label** (not far right — the ASCII spacing above is a monospace
  artifact), drop a short vertical leader; list each ship's transponder code on its
  own line below, in the ship's faction colour. Suppress the normal dot/heading
  for those ships (the label *is* their marker while parked).
- Keep it readable: cap the listed codes (e.g. first N + "+k more") if a body has a
  crowd; only list **tracked/visible** ships (respects Locate/show-hide + the new
  board filter is board-only, so the map shows tracked ships as today).
- Factor the grouping into a small tested helper (`atBodyGroups(ships, bodies)` →
  `Map<bodyId, LiveShip[]>`); the canvas drawing stays in the component.

## Tasks

- [ ] `ui/lib/nation.ts` — nation code→name map + `nationName(code)`; test.
- [ ] `ui/lib/board.ts` — `boardFilter(roster, opts)` (+ list of nations present); test.
- [ ] FleetBoard: filter popover (hide-arrived + nation checkboxes), apply with search.
- [ ] SystemMap: `atBodyGroups` helper (tested) + leader-line render; suppress dots
      for grouped at-rest ships.
- [ ] `just check` green (UI vitest + svelte-check + prettier; engine untouched).

## Acceptance criteria

- The Fleet Board can hide arrived ships and filter by nation (by name); search
  still works on top; a cue shows when a filter is active.
- In a system with ships parked at a planet, the planet's label shows a leader line
  with their transponder codes (left-of-centre indent), and those ships no longer
  render as overlapping dots.
- Ships in motion / queued are unaffected.
- All gates green.

## Out of scope (deferred)

- Repeating routes (#59) — Sprint 033.
- Filtering the *map* by nation (this sprint filters the board only).
- Persisting filter state across reloads.
