# 001 — Gateway systems to build for a workable network

**Question:** which star systems do we pull next so flight plans can actually
cross the wormhole network — starting from the simulator's implemented Sol
System and reaching Manticore and beyond?

## Key insight

The network's nodes are the **terminus systems of the junctions we've captured**,
not "systems we happen to have built." Of our four built systems, only Manticore
and Basilisk are wormhole-connected to each other; Yeltsin's Star and Endicott
are hyperspace-only and sit off the network until Phase 2b. So the build order
below is driven by *connectivity*, not lore prominence.

The Manticore Junction's directly-connected terminus systems (one wormhole
transit from Manticore) are: **sigma-draconis (Beowulf), trevors-star, gregor,
hennesy, matapan, mq-l-1792-46a (Lynx)**, plus already-built **basilisk**. The
Erewhon Junction adds **erewhon, phoenix**, and its Solarian/Sasebo ends.

## Referenced-but-unbuilt systems

(IDs already used in `wormholes/` and `nations/`; building these resolves the
dangling FKs.)

| system_id | Role | Canon data on hand | Wormhole-connected to |
|---|---|---|---|
| `sigma-draconis` | **Beowulf** — Sol's on-ramp to the network | Solarian core world; terminus 475 ly from Manticore | Manticore (Beowulf Terminus) |
| `trevors-star` | San Martin; Manticore member system | terminus 210 ly NE; ex-Havenite | Manticore (Trevor's Star Terminus) |
| `gregor` | Andermani border; Gregor-A Manticoran | terminus 180 ly NW; binary | Manticore (Gregor Terminus) |
| `erewhon` | 2nd junction host; Solarian-adjacent | junction host; ally | (its own 3 termini) |
| `hennesy` | Phoenix Cluster | terminus 712 ly SE | Manticore (Hennesy Terminus) |
| `matapan` | uninhabited terminus system | terminus 472 ly W | Manticore (Matapan Terminus) |
| `mq-l-1792-46a` | Lynx / Talbott gateway | terminus 612 ly SW; surveyed 1919 | Manticore (Lynx Terminus) |
| `phoenix` | Erewhon's Terra Haute end | terminus 390 ly | Erewhon |
| `hancock` | RMN naval base (no member world) | station only | hyper-only |
| `grendelsbane` | RMN base; lost shipyard | station only | hyper-only |
| `elric` | RMN base (destroyed 1914) | station only | hyper-only |
| `cerberus` / `hades` | Havenite prison system (PNS Tepes) | plot site | hyper-only |

## Recommended build order

### Tier 1 — make Sol → Manticore real (do first)
- **`sigma-draconis` (Beowulf).** The single most valuable system to add: it is
  the node the Sol→Manticore route passes through. Without it the route has only
  the fabricated `hyper_leg` stub and no real intermediate system. Pull its star
  data (for the hyper-limit) and confirm/define the Sol↔Beowulf distance (see
  `002`, item 4).

### Tier 2 — a genuinely multi-hop Manticoran network
- **`trevors-star`** — close, canonically rich (San Martin), a member system.
- **`gregor`** — adds the Andermani border flavor and a binary.
- **`erewhon`** — lights up the second junction and the Solarian-side routes.

With Tier 1+2 plus the built Manticore/Basilisk, the wormhole graph becomes a
real network (Sol — Beowulf — Manticore — {Basilisk, Trevor's Star, Gregor} and
the Erewhon spur), enough to exercise multi-system flight planning.

### Tier 3 — fill out coverage
- `hennesy` + `phoenix` (and decide the Phoenix transfer — see `002`),
  `matapan`, `mq-l-1792-46a`.
- The remaining four junctions (Asgard, Felix, Visigoth, Yildun) + the ~14
  bridges, via the `honorverse-wormhole-scribe` skill.
- Plot/base systems (`hancock`, `grendelsbane`, `elric`, `cerberus`) — hyper-only,
  so lower priority until Phase 2b, but cheap to stub for ship/nation FKs.

## Note for the simulator side
Inter-system distances require an **absolute coordinate frame**, which canon does
not provide — see `002`, item 1. Building these systems supplies the relative
bearings/distances to triangulate from, but the frame itself is a decision we
have to make (and fabricate).
