# Planning — Honorverse-Data

Decision and roadmap notes for the **data** project (distinct from the
`hv-simulator` repo's own `planning/` folder, which plans the *engine*). This
folder answers "what do we still need, and in what order" so the dataset stays
ahead of what the simulator needs.

## Documents

- [`001-gateway-systems.md`](001-gateway-systems.md) — which star systems to
  build next so the wormhole network is actually *traversable*, in priority
  order.
- [`002-crucial-data-points.md`](002-crucial-data-points.md) — the data points we
  must lock down (and where we'll have to fabricate) for a workable spatial +
  clock network.
- [`003-readiness-assessment.md`](003-readiness-assessment.md) — "do we have what
  we need?" across the travel stack, with a Sol→Manticore→Yeltsin's worked
  example. Conclusion: the physics layers are in place; the gaps are now spatial.

## Current state (2026-06-13)

Built and synced to `/gratch/Honorverse-Data`:

| Layer | Files | Count |
|---|---|---|
| Systems | `systems/*.json` | 4 (Manticore, Basilisk, Yeltsin's Star, Endicott) |
| Nations | `nations/*.json` | 1 (Star Kingdom of Manticore) |
| Ships | `ships/ship-classes.json`, `ships/ships.json` | 9 classes / 23 ships |
| Wormholes | `wormholes/wormhole-network.json` | 2 junctions, 12 links |
| Hyperspace | `hyperspace/hyperspace.json` | 10 bands + hyper-limit table |
| Schema | `schema/*.json` | 5 |
| Skills | `.claude/skills/honorverse-*-scribe` | 3 (system / ship / wormhole) |

The simulator (`hv-simulator`) implements the **Sol System** (Phase 1) and is
moving toward **Phase 2: the wormhole network** for inter-system flight plans.
Hyperspace is a later phase (call it Phase 2b here).

## The one structural fact that drives the roadmap

Among the **built** systems, only **Manticore ↔ Basilisk** are wormhole-
connected. **Yeltsin's Star (Grayson)** and **Endicott (Masada)** have no
wormhole termini — they're reached by hyperspace and are therefore *isolated*
from the network until Phase 2b. So "more built systems" ≠ "more network": the
network grows by building the Manticore Junction's **terminus systems**. That's
what `001-gateway-systems.md` is about.
