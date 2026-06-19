---
name: atv-add-ship
description: >-
  Intake a community "add a ship" request for the All-The-Vibes (ATV) tribute
  system: read the GitHub issue, add the requested hull to the StarterKit class in
  data/ships/ships.json (next hull code, canon:false, crediting the submitter),
  recompile + verify the transponder, run the gate, ship it, and close the issue
  with the assigned transponder. Use when an "add a ship" / ship-name issue comes
  in for the ATV fleet.
---

# Add an ATV ship (community intake)

A small, repeatable flow for the offer made at the ATV demo: people file a GitHub
issue with a ship name (and optionally a captain), and we add it to the
**All-The-Vibes** system's fleet. Every ATV ship is a **StarterKit**-class personal
transport (`all-the-vibes` nation, code 42), and everything ATV is **`canon:false`**
(a non-Honorverse Easter egg).

Run from the repo root. Takes the **issue number** as input.

## 1. Read the request

```sh
gh issue view <N> --json number,title,author,body
```

Extract from the title/body:
- **Ship name** — the headline. Normalise to a single `ATV <Name>` (add the `ATV `
  prefix if the submitter didn't; keep their capitalisation otherwise).
- **Captain** (optional) — e.g. "Captain Shyam"; goes in the lore credit.
- Ignore anything off-topic; if there's no usable ship name, comment on the issue
  asking for one and stop.

Pick a **slug id**: `atv-<name-lower-hyphenated>` (e.g. `ATV Singularity` →
`atv-singularity`). If it collides with an existing ship id, suffix to disambiguate.

## 2. Pick the next hull code

Hull codes are unique within a class. Find the next free StarterKit hull:

```sh
python3 -c "import json; d=json.load(open('data/ships/ships.json')); \
print(max([x['hull_code'] for x in d['ships'] if x['class_id']=='starterkit'])+1)"
```

The ship's transponder will be `42.1.<hull>` (nation 42 · StarterKit class 1 · hull).

## 3. Append the ship

Append one object to the `ships[]` array in `data/ships/ships.json` (targeted edit
at the array close — preserve the 2-space indent; don't rewrite the file):

```jsonc
{
  "id": "atv-<slug>",
  "name": "ATV <Name>",
  "prefix": "ATV",
  "hull_number": null,
  "class_id": "starterkit",
  "hull_code": <next>,
  "navy": null,
  "affiliation_nation_id": "all-the-vibes",
  "role": "personal transport",
  "status": "active",
  "fate_pd": null,
  "canon": false,
  "source": "community request (GH #<N>)",
  "lore": "Added by community request — GH issue #<N>, submitted by @<login>.<captain line, if any>"
}
```

Keep the lore short, friendly, and in the ATV spirit. No engine, class, or
transponder-codes changes are needed — the StarterKit class + nation 42 already
exist; the compiler assigns the hull/transponder.

## 4. Recompile + verify

```sh
python3 tools/validate-data.py data           # schema check (hull_code must be set)
just compile-data                             # data/ -> build/universe.db
```

Verify the engine resolves the new hull (it should appear on the catalog with the
expected transponder):

```sh
just galaxy-summary | grep -i ships           # count went up by one
# or hit /fleet/ships and confirm "ATV <Name>" -> 42.1.<hull>
```

## 5. Gate + ship

```sh
just check        # engine pytest + ruff + UI; must be green
```

Then ship it like any sprint change — branch, commit, PR, squash-merge (use the
`sprint-ship` skill, or a quick direct commit + PR if a branch is already open).
Commit message: `feat: add ATV <Name> (GH #<N>)`.

## 6. Close the issue

Thank the submitter and record the assigned transponder:

```sh
gh issue close <N> --comment "Welcome to the fleet! **ATV <Name>** is now flying as \
a StarterKit-class personal transport, transponder **42.1.<hull>**. Find it on the \
Fleet Board / in the All-The-Vibes system. Fair winds — thanks for the request! 🚀"
```

## Notes / guardrails

- **canon:false always** — ATV is a non-canon tribute; never flag these `canon:true`.
- **Batch friendly:** multiple requests → assign consecutive hull codes, one ship
  object each; one recompile + gate + ship covers the batch.
- **Keep it kind:** these are community contributions; the lore credit names the
  submitter (and captain). Decline only genuinely inappropriate names — comment
  politely and leave the issue open for a revised name.
- New ATV *classes* (beyond StarterKit) are out of scope here — that's a galaxy
  expansion (`expand-galaxy`), needing a class + transponder code.
