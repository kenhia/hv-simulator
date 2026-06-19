# Galaxy changelog

A human-readable log of how the Honorverse **dataset** grows — systems, ships,
classes, wormholes — complementary to git history. Each entry is a dated
snapshot/delta; counts are generated from the compiled artifact via
`just galaxy-summary` (so they're truth, not memory). Newest first.

Maintained by the `expand-galaxy` skill: every expansion appends an entry.

---

## 2026-06-19 — ATV ship intake: ATV Singularity (Sprint 034, non-canon)

Community ship intake for the All-The-Vibes fleet. Added an `atv-add-ship` skill
that turns an "add a ship" GitHub issue into a StarterKit hull, and processed the
first request: **ATV Singularity** (`atv-singularity`, hull 4, transponder
**42.1.4**), commanded by Captain Shyam — submitted by @shyamsridhar123 (GH #37).
StarterKit class, `all-the-vibes` nation, `canon:false`. Ships count 39 → 40.

## 2026-06-18 — All-The-Vibes tribute system (Sprint 033, non-canon)

A fun, **non-canon Easter egg** (everything `canon:false`) for the All-The-Vibes
(ATV) community — an internal Microsoft community of AI enthusiasts
(https://github.com/All-The-Vibes). Not Honorverse canon; it just lives in the
dataset for the demo.

- **System** **All-The-Vibes** (id `all-the-vibes`, ~250 ly galactic-NE of Sol):
  G2 star **Vibe** with five worlds named for LLMs — **Phi** (small rocky inner),
  **GPT** + **Claude** (habitable; Claude is the capital, Prompt Town), **Gemini**
  and **Llama** (gas giants).
- **Nation** **All-The-Vibes** (transponder code **42**), an "AI Enthusiast
  Collective."
- **Ship class** **StarterKit** (code 1) — a highly experimental 1,200-ton light
  personal transport rated to **927 G** and the **Theta band (8)** (apparent =
  5000 x 0.6c). Hulls: **ATV Phoenix** (42.1.1), **ATV TokenMasterX** (42.1.2),
  **ATV PaperBoard** (42.1.3). Verified: a StarterKit plans + flies a full
  multi-mode route (n-space + Theta hyper + the Manticore Junction).

Counts after: systems 17, nations 11, ship classes 15, ships 39.

## 2026-06-18 — Living galaxy: Haven, Gregor, Erewhon + real nations (Sprint 030)

A demo-weighted expansion. Three systems added/resolved, five nations made real
(no longer compiler stubs), and the Havenite fleet grown.

**Systems** (13 → 16; built 6 → 11):
- **Haven** (new) — capital system of the Republic of Haven (capital world Haven,
  city Nouveau Paris); 667 ly from Earth, ~300 ly from Manticore (HH1/HH3).
- **Gregor** (resolved stub) — **binary**: Gregor-A (F9, uninhabitable) carries the
  Manticoran **Gregor Terminus** of the Manticore Junction; Gregor-B (Andermani)
  holds the system's one habitable world (former Gregor Republic). 180 ly from
  Manticore (HH6).
- **Erewhon** (resolved stub) — K5 system governed by the Republic of Erewhon,
  **host of the Erewhon Wormhole Junction** (the second junction now lands on a
  placed system). East of Manticore, south of Haven.
- **New Berlin** (new) — capital of the **Andermani Empire**, G4 star + capital
  world **Potsdam** + Alpha Station (Imperial Andermani Navy base); ~49 ly from
  Gregor (HH6).
- **Durandel** (new) — Andermani system holding the Durandel Terminus of the
  *Asgard* Junction (Asgard not yet built → lore only, no graph edge).

**Map balance (demo):** the Andermani trio (Gregor, New Berlin, Durandel) is placed
to the galactic **west / left of Manticore** to match a downloaded reference fan map
and fill the empty left of the galaxy view. Canon describes the Andermani as
*east* of Manticore; the westward bearing is deliberate artistic license
(`canon:false`), canon distances preserved (Gregor 180 ly, New Berlin↔Gregor 49 ly).
Several **non-canon planets** were added to Haven, Gregor, New Berlin, and Durandel
so no built system is "star + 1 planet" (all `canon:false`).

**Nations** (now real records): Republic of Haven, Protectorate of Grayson,
Republic of Beowulf, Solarian League, Republic of Erewhon (code 661), and the
**Andermani Empire** (code 734). Every built system's affiliation is authored.

**Ships** (33 → 36): +3 canon People's Navy **Sultan-class** battlecruisers (PNS
Barbarossa, Mehmed, Murad), growing the Havenite fleet on the board to 7.

**Placement model (Sprint 028 → refined):** the bearing-arc deflection is now
floored to **|θ| ∈ [3°, 22.5°]** (no system sits ~on a cardinal — fixes the old
near-axis cases like Basilisk/Trevor's) and a system may store an explicit
**`location.bearing_offset_deg`** (random-at-incorporation, frozen for stable
coords). **All coordinates were regenerated**; existing systems shifted within
their canon distances (canon:false bearings only). Trevor's Star converted to an
explicit +12° offset (was a +10° nudge) so its tuning is decoupled from the hash.

Counts after: systems 16 (11 built), stars 13, bodies 49, places 24, nations 10,
ships 36. Placed systems (Sol-galactic frame, ly): basilisk (−123.5, 700.4),
durandel (−358.7, 476.0), endicott (−122.0, 522.6), erewhon (+102.7, 448.9), gregor
(−321.0, 522.7), haven (+43.1, 726.2), manticore (−143.7, 491.4), new-berlin
(−353.1, 559.7), sigma-draconis (+6.0, 39.6), trevors-star (+61.7, 535.1),
yeltsins-star (−120.5, 512.0); Sol at the origin. The Andermani cluster (gregor,
new-berlin, durandel) anchors the galactic-west/left of the view.

_Deferred:_ Beowulf / Erewhon ship rosters (their System-Defense / shipyard navies
aren't well-specified in canon — left rather than fabricated). Andermani Empire not
authored as a nation (Gregor's system-level affiliation set to Manticore, the
terminus owner; Gregor-B's Andermani ownership is in lore).

## 2026-06-18 — Bearing-arc galactic spread (Sprint 028)

The frame tool (`tools/coordinate-frame`) now applies a deterministic **±22.5°
bearing-arc jitter** to each system's placement (a `canon:false` artistic-license
spread within the canon compass wedge), so systems sharing a coarse bearing no
longer stack on one axis. **All placed-system coordinates were regenerated**
(`just frame` → `just compile-data`); canon **distances are preserved** (the jitter
is a pure in-plane rotation), only the in-bearing direction shifted. The galaxy map
reads as a believable spread instead of a vertical X=0 column. The jitter is a
stable hash of the system id — re-running the tool reproduces identical coordinates.

A per-system hand-tune hook accompanies the auto spread: an optional
`location.bearing_nudge_deg` (canon:false, +CCW in the galactic plane, additive to
the jitter) rotates a system's placement about its reference for cases where the
seeded spread reads wrong. **Trevor's Star** carries a +10° nudge (rotated ~10°
counter-clockwise about Manticore, its placement reference; the 210 ly canon
terminus span is preserved) for a more natural layout.

Placed systems (Sol-galactic frame, ly): basilisk (+3.9, +703.1), endicott
(−53.8, +540.7), manticore (−71.3, +507.0), sigma-draconis (+15.2, +37.0),
trevors-star (+136.1, +540.0), yeltsins-star (−47.7, +527.1); Sol at the origin.
No systems/ships/classes added — placement only.

## 2026-06-16 — Wormhole transit queues (Sprint 019, Phase 2c)

The engine's **first stateful resolver**. A ship reaching a wormhole junction now
joins a **transit queue** instead of translating instantly: the nexus
destabilises for `interval = max(tau(M), buffer)` after each transit, so transits
serialise. A ship reports `queued` with a **position** (`#3 -> #2 -> #1 -> pops`)
and a transit ETA, counting down as sim time advances — all analytic on the
discrete-event core, no per-tick loop. Queue depth comes from two sources: a
fabricated per-junction **`traffic_intensity`** knob (Manticore Junction busy = 6,
Erewhon quiet = 1) drives a seeded **phantom-traffic** stream (Poisson-drawn, a
pure function of `(seed, junction, transponder)` — reproducible, never a
constant), and other filed ships **interleave deterministically** by arrival
(stable-key tiebreak). Try it: `just queue-demo` (two RMN cruisers into the
Manticore Junction). **Contract -> v0.4.0** (`wormhole_junctions.traffic_intensity`).
The deployed `/fleet` queue board is Sprint 020.

---

## 2026-06-16 — Transponder ship identity (Sprint 017)

A data/identity change (no new astrography). Every ship now has a canonical
**`nation.class.hull`** transponder built from stable integer codes in
`data/transponder-codes.json`, plus an engine-only `modified` bit (set when a hull
overrides its class). Nation codes are non-sequential for a lived-in feel: **0**
unaffiliated, **1** Sol (Solarian League), **2** Beowulf (reserved), others
random-ish in [42, 999]. All 33 ships got unique transponders (e.g. SLNS *Nevada*
= `1.2.3`, GNS *Honor Harrington* = `213.1.1`). Slug ids stay the primary keys
(transponder supplements). **Contract → v0.3.0.** Sets up the deployed galaxy
service (Sprint 018) and Phase-3 combat/narrative (where transponders + false-flag
matter). Realizes kwi #65.

---

## 2026-06-16 — Hyperspace band model + ship tech-data model (Sprint 015)

A modeling change rather than new astrography. Encoded **David Weber's own
"Effective Speed By Hyper Band" chart** into `data/hyperspace/hyperspace.json`:
per-band `velocity_multiplier` + `translation_bleed_off_pct` (canon), with
`apparent = multiplier × real_cruise_velocity` (warship 0.6c / merchant 0.5c).
See [data/README.md](../data/README.md) for the source + copyright note (the
chart is "All Rights Reserved"; authorization to be sought at v1.0.0+).

Ship tech-data model: each `ship_class` now carries a **`max_hyper_band`**
(inferred by hull type — warships Zeta/Eta, merchants Delta, canon:false) and a
real cruise velocity; an individual ship can **override** class stats
(`ovr_*` → effective = class ⊕ override). Every ship must resolve to a class
(classless → auto `singleton` class). **Contract → v0.2.0.**

Counts unchanged (13 systems / 14 classes / 33 ships); the artifact gains the
`hyperspace_model` globals row. Effect: interstellar trips now vary by ship —
e.g. a Nike-class BC (Eta) flies Sol→Grayson in ~11.1 d vs a Starhauler freighter
(Delta) in ~26.2 d (was a flat 130 d under the 014 single-band placeholder).

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
