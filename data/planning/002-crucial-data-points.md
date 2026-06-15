# 002 — Crucial data points to lock down

What the dataset must nail (and where we must fabricate) for a workable spatial +
clock network. Ordered by how much they block Phase 2. Each notes **why it
matters for a clock simulator**, its **canon status**, and a **proposed
approach**.

Convention reminder: anything we invent is recorded with `canon: false` (and, for
numeric fields, listed in a `derived` array) so fabrication is always visible.

---

## 1. Absolute galactic coordinate frame  ⬅ highest priority

- **What:** a 3D position for every system. Right now all locations are
  *relative* ("512 ly galactic-north of Sol", terminus "210 ly Galactic North",
  etc.) — there is no common origin or axis convention.
- **Why it matters:** inter-system distances (for hyper legs, for any map, for
  "where is everything right now") are impossible without absolute coordinates.
- **Canon status:** **none.** Canon gives bearings and distances relative to Sol
  or Manticore, never absolute galactic coordinates.
- **Proposed approach:** define a fabricated frame — origin at **Sol**, axes
  aligned to the canon "Galactic North/South/East/West" usage, +Z = galactic
  north. Convert each system's canon distance+bearing into XYZ; triangulate using
  the multiple known bearings (e.g. Manticore from Sol, and termini distances
  from Manticore) to cross-check. Store under a `coordinates` block, `canon:false`.
  This frame becomes the backbone every other spatial field hangs on.

## 2. Wormhole nexus & terminus in-system positions

- **What:** where, inside a system, each junction nexus and terminus sits.
- **Why it matters:** a ship must fly (normal-space, real clock time) from its
  start to the nexus/terminus before transiting, and from the far terminus to its
  destination. Without a position there is no in-system leg to time.
- **Canon status:** almost none. The **one** datum is the Manticore nexus at
  **7 light-hours from Manticore-A** (canon). Forts sit ~500,000 km from a
  terminus (a defensive detail, not a position).
- **Proposed approach:** adopt a placement convention — e.g. put each terminus
  near the system's **hyper-limit** (item 3) at a chosen bearing, `canon:false`,
  `determined:true` once set. Keep Manticore's 7-light-hour nexus as the canon
  anchor and the template for scale.

## 3. Hyper-limit and primary stellar data per system

- **What:** each system's hyper-limit radius — a function of the primary star's
  mass — and therefore the star's mass/spectral type.
- **Why it matters:** ships drop sublight at the hyper-limit; it sets where
  inbound ships appear and is the natural anchor for terminus placement (item 2)
  and arrival legs.
- **Canon status:** partial. We have spectral types for built systems (Manticore
  G0/G2, Basilisk G5, Yeltsin's F6, Endicott K4) and masses for a few
  (Manticore-A/B). Gateway systems mostly lack stellar mass.
- **Proposed approach:** where canon gives spectral type but not mass, fabricate
  mass from a standard main-sequence type→mass table (`canon:false`), then derive
  the hyper-limit. Pull each gateway system's star data when building it (per
  `001`).

## 4. Sol ↔ Beowulf distance and the hyperspace model

- **What:** the Sol→Sigma-Draconis (Beowulf) leg — currently a `canon:false`
  `hyper_leg` stub with a null distance.
- **Why it matters:** it is the *only* non-wormhole hop on the Sol→Manticore
  route. To time it we need the distance and a hyperspace speed model.
- **Canon status:** distance not yet captured (real-world Sigma Draconis ≈ 18.8
  ly from Sol; the Honorverse figure should be confirmed). Hyperspace has canon
  mechanics (bands/translation) not yet modeled.
- **Proposed approach:** when building `sigma-draconis`, scrape the Sol↔Beowulf
  distance. Defer the full hyperspace speed model to Phase 2b; until then the
  router treats this edge as a placeholder so end-to-end Sol→Manticore planning
  works.

## 5. Junction transit timing (the clock cost of a transit)

- **What:** how long a junction transit really costs on the clock.
- **Why it matters:** transit is "instantaneous" *through* the wormhole, but a
  junction has a **mandatory interval between transits** and Astro-Control
  queuing — so a transit is not free in wall-clock terms. The sim's whole value
  is "realism of the clock," so this can't be hand-waved to zero.
- **Canon status:** qualitative (the Royal Manticoran Astro-Control Service meters
  traffic; mass/proximity limits exist) but no clean number captured yet.
- **STATUS — ADDRESSED (2026-06-14):** a fabricated model now lives in
  `wormholes/wormhole-network.json` → `transit_model`. The mechanic is book-canon
  (mass-scaled destabilization; sequential vs. mass-transit tradeoff; ~48 h for a
  large fleet) but the wiki gives no numbers, so the model is `canon:false`.
  Form: `destabilization_seconds = A·√M + B·M²` (M = tons transited per event),
  with A=0.01684, B=6.9e-13, anchored on a light cruiser (5 s), a medium freighter
  (~26 s), and a ~500 Mt fleet mass-transit (~48 h). The √M term gives per-ship
  seconds (queue granularity); the M² term gives the steep fleet cost. Open: pin
  a real number from the novels if one exists; add a settling floor / junction-size
  tolerance later.

## 6. Orbital elements for system bodies (carried over)

- **What:** Keplerian elements (a, e, i, …) for planets/moons so the ephemeris
  can place them; mostly null today.
- **Why it matters:** in-system flight legs (planet → terminus, etc.) need body
  positions over time.
- **Canon status:** ordering is canon; elements are not. A few anchors exist
  (Manticoran year = 1.73 T-yr; Medusa ~7 lm; Grayson ~13.5 lm; Masada ~¼ of
  Grayson).
- **Proposed approach:** derive first-pass elements from the anchors + the
  hyper-limit scale, `canon:false`, `determined:true`. This was already on the
  follow-up list.

---

## Resolved / not blocking
- **Ship acceleration & compensator margin** — handled. `acceleration.max_g` is
  the sim's `max_accel_g`; the normal:max ratio varies by class and is captured
  per class; single-value classes read as max with a derived 80% normal.

## Suggested sequence
1. Define the **coordinate frame** (item 1) — unblocks everything spatial.
2. Build **`sigma-draconis`** with star data + Sol↔Beowulf distance (items 3–4).
3. Set a **terminus-placement convention** off the hyper-limit (item 2).
4. First-pass **orbital elements** (item 6) and **transit timing** (item 5).
