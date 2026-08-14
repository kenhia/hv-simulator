# Sprint 038 — onto the kprojects harness

Put this repo on the shared **kprojects minimal harness**
(<https://github.com/kenhia/kprojects>) so it carries the same managed
instruction block, layout and gate convention as the rest of Ken's projects.
korg **#1236** (proposal #1241), batch 1 of the rollout from korg #737 —
the three kai skills-only repos (kvllm, kmon, hv-simulator).

**A chore sprint: no behaviour change.** Nothing in `engine/`, `tools/`,
`data/`, `contracts/` or `ui/` changes semantics. The only code touched is one
docstring path reference.

## The one thing that makes this repo different

Stack detection reads the **repo root** (`Cargo.toml` → `go.mod` →
`pyproject.toml`, first match wins). This repo's Python lives one level down in
`engine/`, so the root has only a `justfile` and a bare run would report
`stack : other (detected)` — seeding a **TODO** gate inside a managed block
that cannot be hand-corrected afterwards, only re-applied.

So the installer was run with an **explicit `--stack python`**:

```sh
uvx --refresh --from git+https://github.com/kenhia/kprojects \
    kproject-install --agent both --stack python .
```

It printed `stack : python (given)`, which is the check that matters.

(Arguably a gap in kprojects' root-marker detection for repos with a nested
app. Worth a kprojects work item if a second repo hits it; not this sprint's
job to fix.)

## Decisions

- **The `justfile` is load-bearing and was left alone.** It carries the
  deploy/ops recipes (`set dotenv-load := true`, `HVSIM_HOST`/`HVSIM_PORT`
  from `.env`, a tailscale-serve-aware client base URL) *and* an already-real
  `check` recipe. The installer only seeds a justfile when one is missing, so
  it was untouched — verified with `git diff --quiet justfile`.
- **`.gitignore` was untouched too.** All five entries the python stanza would
  add (`.scratch/`, `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`) were
  already present, so the existing `!.env.example` negation is undisturbed.
- **Root `planning/` folded into `sprints/planning/`** rather than left as a
  parallel set beside the one the harness creates. The seven design docs
  (`001`–`007`) moved with `git mv`; every reference was rewritten per
  location, since they are relative markdown links (`../planning/` from
  `sprints/` became `planning/`; `ui/README.md` gained a level; root files
  became `sprints/planning/`). `data/planning/` is a **different** directory
  (the dataset's own) and an external `/gratch/Honorverse-Data/planning/`
  reference in `006` was left alone.
- **The managed block leads `CLAUDE.md`**, matching every sibling repo; the
  pre-existing content moved under a `## Project` heading and its sections were
  demoted one level. Content outside the block is ours; inside is never
  hand-edited.
- **`.github/copilot-instructions.md` gets a condensed `## Project`**, not a
  copy of `CLAUDE.md`'s 300 lines — the same convention kaed uses for a repo
  with a large CLAUDE.md. Same facts, less detail; both are maintained.
- **`sprints/review/` stays uncommitted** while empty. No sibling repo carries
  a `.gitkeep` there.

## Tasks

- [x] Branch `sprint-038-kprojects-harness`; clean tree confirmed.
- [x] Run the installer with `--agent both --stack python`; confirm it prints
      `stack : python (given)`.
- [x] Verify the `justfile` and `.gitignore` are unchanged.
- [x] Fold root `planning/` into `sprints/planning/`; rewrite every reference
      and confirm no markdown link dangles.
- [x] Restructure `CLAUDE.md` (block first, project content under `## Project`).
- [x] Write the `## Project` section in `.github/copilot-instructions.md`.
- [x] Fill `sprints/planning/roadmap.md` (Now / Next / Later) from the design
      docs and the project's open korg work items.
- [x] `just check` green.

## Acceptance criteria

- The managed block is present between the markers in both `CLAUDE.md` and
  `.github/copilot-instructions.md`, with the **python** tooling stanza, and
  is unedited inside.
- `sprints/planning/`, `sprints/review/`, `docs/` and `.scratch/` all exist;
  `.gitignore` carries `.scratch/` and `.env`.
- `just check` still runs the real engine + tools + data + UI gate — not a
  seeded TODO — and passes.
- The deploy recipes (`deploy`, `health`, `fleet`, `seed`, …) are intact.
- No root `planning/` directory remains, and no reference to it dangles.

## Out of scope

- Fixing kprojects' stack detection for nested-app repos.
- Any change to the engine, tools, dataset, contracts or UI beyond a single
  docstring path.
