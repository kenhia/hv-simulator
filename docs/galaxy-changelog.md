# Galaxy changelog

A human-readable log of how the Honorverse **dataset** grows — systems, ships,
classes, wormholes — complementary to git history. Each entry is a dated
snapshot/delta; counts are generated from the compiled artifact via
`just galaxy-summary` (so they're truth, not memory). Newest first.

Maintained by the `expand-galaxy` skill: every expansion appends an entry.

---

## 2026-06-15 — Expansion: Beowulf + Trevor's Star, Solarian Nevada class

First Phase 2a.1 expansion — proves the data→artifact→engine pipeline handles
real dataset growth end-to-end (scribe → orbit-derive → frame → compile →
engine verify). Two stubbed wormhole termini become real systems.

**Added**

- **Sigma Draconis (Beowulf)** — Solarian K0 system 40 ly from Sol on the
  Sol-Manticore line. Worlds: Beowulf (humanity's first extrasolar colony,
  biosciences capital) and Cassandra; gas giant Enlil; the Diomedes Belt. Hosts
  the Beowulf Terminus of the Manticore Junction — the principal Manticore↔Solarian
  gateway.
- **Trevor's Star** — G2 system 210 ly galactic-east of Manticore (former Havenite
  space). Sole world: the high-gravity San Martin. Holds the Trevor's Star Terminus
  of the Manticore Junction.
- **Nevada class** (Solarian League Navy battlecruiser, intro 1920 PD) — first SLN
  hull in the dataset; 911,250 t, 487.7 G max, crew ~3,000. Ships: SLNS *Nevada*,
  *Camperdown*, *Jean Bart*.

**Resolved stubs → built:** `sigma-draconis`, `trevors-star` (were bare wormhole
termini; now carry stars, bodies, frame coordinates).

**Verified in the engine:** both systems place in the frame (Sigma Draconis at
(0,0,40) ly, Trevor's Star at (210,0,512) ly); bodies are placeable; the Manticore
wormhole links resolve (475 ly to Sigma Draconis, 210 ly to Trevor's Star);
`inter_system_distance` returns Sol↔Sigma-Draconis = 40 ly (frame) and the
Manticore links via canon wormhole spans. Nevada class + 3 ships compile.

**Count deltas (vs. baseline):** systems built 4 → 6 (stubbed 9 → 7) · stars
5 → 7 · bodies 31 → 35 · belts 5 → 6 · places 17 → 20 · ship classes 13 → 14 ·
ships 30 → 33. Contract unchanged (v0.1.1); nations unchanged (7 — `solarian-league`
was already referenced).

```
- **Contract** v0.1.1
- **Systems** 13 — built (6): basilisk, endicott, manticore, sigma-draconis, trevors-star, yeltsins-star
  - stubbed (7): erewhon, gregor, hennesy, matapan, mq-l-1792-46a, phoenix, sol
- **Stars** 7 · **Bodies** 35 · **Belts** 6 · **Places** 20
- **Nations** 7
- **Ship classes** 14: atlas-manticore, courageous, dromedary, edward-saganami, honor-harrington, invictus, nevada, nike, raoul-courvosier-ii, reliant, star-knight, starhauler, sultan, warlord
- **Ships** 33
- **Wormhole** junctions 2, links 12
- **Hyperspace** bands 10, hyper-limits 44
```

---

## 2026-06-15 — Baseline (pre-expansion)

State after Phase 2a (Sprints 010–011): the four scribed systems placed in the
galactic frame, the wormhole network + hyperspace model compiled in. Captured
before the first Phase 2a.1 expansion.

- **Contract** v0.1.1
- **Systems** 13 — built (4): basilisk, endicott, manticore, yeltsins-star
  - stubbed (9): erewhon, gregor, hennesy, matapan, mq-l-1792-46a, phoenix, sigma-draconis, sol, trevors-star
- **Stars** 5 · **Bodies** 31 · **Belts** 5 · **Places** 17
- **Nations** 7
- **Ship classes** 13: atlas-manticore, courageous, dromedary, edward-saganami, honor-harrington, invictus, nike, raoul-courvosier-ii, reliant, star-knight, starhauler, sultan, warlord
- **Ships** 30
- **Wormhole** junctions 2, links 12
- **Hyperspace** bands 10, hyper-limits 44

(Stubbed systems are referenced by wormhole termini / nation capitals but not yet
built; building them resolves the stubs. Sol is a stub here only as a wormhole
endpoint — the engine places Sol via its real JPL ephemeris, not the artifact.)
