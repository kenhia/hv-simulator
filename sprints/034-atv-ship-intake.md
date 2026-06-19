# Sprint 034 — ATV ship intake (community ship requests)

A quick sprint born from the demo: at the All-The-Vibes (ATV) demo we offered that
people can **file a GitHub issue to add a ship** to the ATV fleet. This sprint adds
a repeatable **skill** for that intake and processes the **first request**.

Plan: follows the Sprint-033 ATV Easter egg. Data + tooling only.

## Goal

- A `atv-add-ship` skill (`.claude/skills/atv-add-ship/`) that turns an "add a ship"
  GitHub issue into a new **StarterKit**-class hull in the All-The-Vibes system,
  recompiles + verifies, ships it, and closes the issue with the assigned
  transponder.
- Process the first issue: **GH #37 — "ATV Singularity"** (Captain Shyam, submitted
  by @shyamsridhar123).

## What it does (the skill flow)

1. `gh issue view <N>` → ship name (+ optional captain). Normalise to `ATV <Name>`,
   slug `atv-<name>`.
2. Next StarterKit hull code → transponder `42.1.<hull>`.
3. Append one ship object to `data/ships/ships.json` (StarterKit / `all-the-vibes` /
   `canon:false`, lore crediting the submitter + captain). No engine / class /
   transponder-code changes (those already exist).
4. `validate-data` → `just compile-data` → verify the hull resolves on the catalog.
5. `just check`; ship (branch → PR → squash-merge); `gh issue close` with the
   transponder + a thank-you.

## This sprint's work

- [x] Author `.claude/skills/atv-add-ship/SKILL.md` (the intake runbook).
- [x] Add **ATV Singularity** — `atv-singularity`, hull 4, transponder **42.1.4**,
      StarterKit class, credited to @shyamsridhar123 / Captain Shyam (GH #37).
- [x] Recompile + verify (catalog shows ATV Singularity → 42.1.4); `just check` +
      `contracts` green.
- [ ] Ship + close GH #37.

## Acceptance criteria

- The `atv-add-ship` skill exists and documents the full intake → close flow.
- ATV Singularity is in the artifact (transponder 42.1.4) and on the fleet catalog.
- GH #37 closed with the assigned transponder; all gates green.

## Notes

- ATV is **non-canon** (`canon:false`); the skill enforces that.
- Batch-friendly: multiple requests → consecutive hull codes in one pass.
- New ATV *classes* (beyond StarterKit) remain an `expand-galaxy` job (class +
  transponder code), not this skill.
