# Sprints

Lightweight execution tracking — deliberately *not* a spec framework (no SpecKit,
no ATV). Each sprint is one short markdown file you and Claude can both read at a
glance. The planning docs in `planning/` say *what we're building and why*;
the sprints here say *what we're doing next and how we'll know it's done*.

## Convention

- One file per sprint: `NNN-short-name.md`, numbered in order.
- Sprints map roughly to the milestones in `planning/004-project-plan.md`.
- Keep each sprint **small enough to finish and verify** — if a task list grows
  past ~8 items or mixes unrelated concerns, split it.

## Each sprint file has

| Section | Purpose |
|---|---|
| **Goal** | One sentence. What capability exists at the end that didn't before. |
| **Scope** | The handful of things this sprint will do. |
| **Out of scope** | Explicit fence — things a reader might *assume* are included but aren't. This is the anti-scope-creep tool. |
| **Tasks** | `- [ ]` checklist, ordered. Check off as completed. |
| **Acceptance criteria** | Verifiable statements. "Done" means every one is demonstrably true (a passing test, a command that prints the right thing). |
| **Notes / decisions** | Anything decided mid-sprint worth remembering. |

## Status

- A sprint is **done** only when every acceptance criterion is verified, not when
  the tasks are checked off. Tasks are the plan; acceptance criteria are the proof.
- Record per-sprint outcomes at the bottom of the file rather than deleting it —
  the sprint history is the project's changelog.
