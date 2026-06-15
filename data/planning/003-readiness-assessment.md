# 003 — Readiness assessment: do we have what we need?

Goal under test: a **navigable galaxy** — flight plans that cross star systems
using normal-space travel, hyperspace, and wormholes, with the simulator's
"realism of the clock." This is the check-in to feed the next planning round.

Short answer: **the physics layers are essentially in place; the gaps are now
spatial (positions/distances), not mechanical.** With hyperspace + hyper-limits
captured this round, the remaining blockers are the coordinate frame, a handful
of gateway systems, and some in-system positions — all already on the backlog.

## Readiness matrix

| # | Layer | Status | What's there | What's missing |
|---|---|---|---|---|
| 1 | In-system normal-space travel | **Have** (sim Phase 1) | Kinematics + ephemeris engine | Body **orbital elements** mostly null (have anchors) — `002 #6` |
| 2 | Hyper-limit (where you can translate) | **Have** (this round) | Full table by spectral class | Star class for **unbuilt** gateway systems |
| 3 | Hyperspace inter-system travel | **Have** (this round) | Band apparent-velocity model (canon + interpolated) | "Max real velocity" (~0.8c?) unconfirmed |
| 4 | Inter-system distance | **Partial** | Many **canon pairwise** distances (e.g. Manticore↔Yeltsin's 31 ly) | A general **coordinate frame** — `002 #1`; Sol↔Beowulf specifically |
| 5 | Wormhole transits | **Have** | Network graph, nexus↔terminus rule | Junction **transit timing** (clock cost) — `002 #5` |
| 6 | Coordinate frame / Galactic Map | **Missing** | — | The keystone for the general case — `002 #1` |
| 7 | Terminus / nexus in-system positions | **Missing** | Manticore nexus (7 lh) only | A placement convention off the hyper-limit — `002 #2` |

## Worked example — can we fly Sol → Manticore → Yeltsin's Star?

Tracing every leg shows exactly where the holes are (and how few remain):

| Leg | What happens | Have? |
|---|---|---|
| A | Depart Sol; climb past Sol's hyper limit (G2 → **21.12 lm**) and translate up | ✅ limit; ✅ kinematics |
| B | Hyper Sol → Beowulf (Sigma Draconis), e.g. Zeta band **2500 c** | ✅ band speed · ❌ **Sol↔Beowulf distance** |
| C | Drop sublight beyond Beowulf's hyper limit; fly to the Beowulf Terminus | ❌ Beowulf star class · ❌ terminus position |
| D | Wormhole transit Beowulf Terminus → Manticore nexus (instant) | ✅ transit · ⚠️ timing cost |
| E | Manticore nexus (7 lh from Manticore-A) → fly to destination planet | ✅ nexus dist · ⚠️ orbital elements |
| F | Hyper Manticore → Yeltsin's Star, **31 ly (canon)** | ✅ limit (G0 22.0 lm) · ✅ **distance** · ✅ band |
| G | Drop beyond Yeltsin's hyper limit (F6 **23.76 lm**); fly to Grayson (~13.5 lm) | ✅ limit · ✅ orbit anchor |

**Finding:** the *entire* second hop (Manticore → Yeltsin's Star) is computable
**today** — the 31 ly distance is canon, both hyper limits are in the table, and
the band model gives the speed (≈4.5 days at Zeta, ≈1.7 days at Theta). The only
hard-missing numbers for the whole itinerary are the **Sol↔Beowulf distance** and
the **Beowulf system** (star class + terminus position). Build Beowulf and the
route is end-to-end.

This is the nuance worth carrying into planning: **the coordinate frame is the
keystone for the *general* case, but many specific, useful routes have canon
pairwise distances and are flyable without it.** We are not blocked from
demonstrating inter-system flight — we're blocked from doing it *everywhere*.

## What we deliberately deferred (and confirmed is safe to)

Gravity waves, the Tellerman wave, grav-wave **sail riding** (the Warshawski-sail
speed bonus), and **dimensional shear** beyond the basic hyper-limit rule. These
change *optimal* routing and achievable speed, but none is required for a
baseline navigable galaxy. Revisit when we want realistic "fast lanes" and
weather-like routing.

Also unconfirmed (minor): the **n-space max velocity** (~0.8c particle-shielding
ceiling) is not on the pages we scraped; the sim currently uses 0.6c for a
merchant. Worth pinning from a primary source.

## Recommended next actions (for the next planning round)

1. **Build `sigma-draconis` (Beowulf)** + capture the Sol↔Beowulf distance.
   Single highest-value item: it closes the only hard gap in the Sol→Manticore
   route. (`001` Tier 1.)
2. **Define the coordinate frame** (`002 #1`). Turns scattered canon pairwise
   distances into a uniform "distance between any two systems," unblocking the
   general hyperspace case and any map.
3. **Terminus-placement convention** off the hyper-limit (`002 #2`) — gives the
   in-system legs to/from termini (Legs C and E).
4. **First-pass orbital elements** (`002 #6`) — gives the in-system legs to
   planets.
5. **Junction transit timing** (`002 #5`) — makes wormhole transits cost real
   clock time.

With 1–3 done, an end-to-end Sol → Manticore → Yeltsin's Star flight plan is
demonstrable; 4–5 refine the clock accuracy.

## Architecture note (simulator side, not data)
Phase 2 needs the engine to model **multiple systems + a galactic frame** and to
**switch travel modes** (n-space ↔ hyper ↔ wormhole) within one flight plan. The
data is now largely ready to feed that; the coordinate frame (item 2) is the main
piece both sides depend on.
