---
name: honorverse-wormhole-scribe
description: >-
  Discovers and captures Honorverse wormhole junctions, bridges, and termini
  into the wormhole network graph for the hv-simulator dataset. Use when adding
  inter-system wormhole connections — e.g. "add the Asgard junction", "capture
  the Congo wormhole bridge", "finish the wormhole network", "wire system X into
  the junction map". Covers index/category discovery, the nexus<->terminus-only
  transit rule, mapping termini and their canonical light-year distances into
  wormhole-network.json, building the derived routing-links graph, and flagging
  fabricated in-system positions and hyper/transfer edges as non-canon.
---

# Honorverse Wormhole Scribe

Build and extend the wormhole network graph for the `hv-simulator` dataset — the
data that lets flight plans cross from one star system to another. Primary
source the David Weber novels; secondary the Honorverse Wiki (CC BY-SA 3.0 — see
`ATTRIBUTION.md`).

All paths are relative to the **dataset root** (the directory holding
`wormholes/`, `systems/`, `schema/`, `ATTRIBUTION.md`). This skill lives at
`.claude/skills/honorverse-wormhole-scribe/`.

## Ground truth to read first

1. `schema/wormhole.schema.json` — the contract.
2. `wormholes/wormhole-network.json` — the **gold reference**; mirror it exactly
   (the Manticore + Erewhon junctions show the full shape).
3. `ATTRIBUTION.md` — source-tag legend.

## The mechanics that drive the model

- A **junction** has a central **nexus** (a point in its HOST system) plus
  several **termini** (points in far systems). **Ships transit nexus<->terminus
  only — never terminus<->terminus directly.** So a junction connects its host
  system to each terminus system; getting between two terminus systems means two
  transits through the nexus.
- A **bridge** is a two-ended wormhole (there-and-back between two termini).
- A **quasi-junction** is a junction in the traffic sense but not the
  astrophysical one (e.g. a terminus of one junction sitting in the same system
  as a terminus of another). Model it as a `transfer` link, not a true junction.
- Transit is **~instant** regardless of the wormhole's light-year "length".
- Termini are rarely located precisely in canon — forts sit ~500,000 km out, but
  the terminus's system-relative position is almost always uncharted.

## Workflow

### 1. Discover

The wiki's two concept pages are the index (better than the category):

```sh
python .claude/skills/honorverse-wormhole-scribe/scripts/fetch_wikitext.py "Wormhole junction"
python .claude/skills/honorverse-wormhole-scribe/scripts/fetch_wikitext.py "Wormhole terminus"
```

`Wormhole junction` lists every junction (with terminus counts), bridge, and
quasi-junction. `Wormhole terminus` lists the termini grouped under each
structure. As of this writing there are **6 true junctions** (Asgard, Erewhon,
Felix, Manticore, Visigoth, Yildun) plus ~14 bridges — small enough to finish.
`list_category.py "Wormhole Junctions"` is a cross-check.

### 2. Scrape each junction/bridge

```sh
python .claude/skills/honorverse-wormhole-scribe/scripts/fetch_wikitext.py "Asgard Wormhole Junction"
```

Capture: host system (where the nexus is), nexus astrophysics if given (node
diameter, distance from primary — usually absent), and each terminus's
**name, far-end system, light-year distance, galactic direction, discovery
date, and controlling nation**. The junction page's "Known termini" section is
the payload; cross-check the `Wormhole terminus` page for the terminus list.

### 3. Map into the schema

- `junctions[]`: one object per junction/bridge with `class`
  (`junction`/`bridge`/`quasi-junction`), `host_system_id`, `controlled_by`,
  `nexus{}`, and `termini[]`.
- Each terminus: `leads_to_system_id` (FK to a system file — coin a
  lowercase-hyphen id even if that system isn't built yet; null if the far
  system is unnamed in canon), `distance_ly`, `direction`, `discovered_pd`.
- The central terminus (the one in the host system) gets `is_nexus: true`,
  `distance_ly: 0`.

### 4. Canon vs fabricated

- Terminus **light-year distance and far-end system are usually canon**; set
  `canon: true` with a `source`.
- **In-system `position` is almost always non-canon** — `canon: false,
  determined: false`. The one known exception so far is the Manticore nexus
  (7 light-hours from Manticore-A, canon).
- Never invent a terminus or destination not in a source.

### 5. Build the routing links

For each external terminus, add a `links[]` edge of `type: "wormhole"` whose two
endpoints are **the host system and the terminus's far system**, with
`via_junction` set and the canon `distance_ly`. This automatically encodes the
nexus<->terminus rule (every wormhole edge has the host system as an endpoint, so
the router can never shortcut terminus-to-terminus).

Two non-wormhole link types exist for gluing the graph together, both
`canon: false`:
- `hyper_leg` — ordinary hyperspace travel (out of scope until Phase 2b); used to
  attach systems with no terminus (e.g. Sol attaches via Beowulf/Sigma Draconis).
- `transfer` — a fabricated short leg bridging two termini that share a region
  (e.g. Phoenix Cluster). Use sparingly and flag clearly.

### 6. Attribute and validate

- Append the junction page(s) to the `ATTRIBUTION.md` source table with the date.
- Append to `wormholes/wormhole-network.json` (`junctions[]` and `links[]`) —
  don't overwrite existing entries.
- Validate: the file parses; every `links` endpoint with a non-null
  `system_id` is consistent; the intended route is reachable. Quick BFS check:

```sh
python - <<'PY'
import json, collections
net=json.load(open("wormholes/wormhole-network.json"))
adj=collections.defaultdict(list)
for l in net["links"]:
    a,b=[ (e["system_id"] or e["label"]) for e in l["endpoints"] ]
    adj[a].append(b); adj[b].append(a)
def reach(s,d):
    seen={s}; q=collections.deque([s])
    while q:
        n=q.popleft()
        if n==d: return True
        for m in adj[n]:
            if m not in seen: seen.add(m); q.append(m)
    return False
print("sol->manticore reachable:", reach("sol","manticore"))
PY
```

## Output checklist

- [ ] Each junction has host_system_id, nexus, and termini with ly-distances.
- [ ] In-system positions flagged `canon:false` (except where canon gives one).
- [ ] A `wormhole` link per external terminus, host system as an endpoint.
- [ ] Fabricated `hyper_leg`/`transfer` edges flagged and explained.
- [ ] `ATTRIBUTION.md` updated; file parses; intended routes reachable.
