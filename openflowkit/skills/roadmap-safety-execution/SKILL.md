---
name: roadmap-safety-execution
description: Plans and executes roadmap work in one-by-one low-risk change-sets with mandatory gates (feature flags, tests, rollback path, and acceptance checks). Use for multi-phase delivery where regressions must be minimized.
---

# Roadmap Safety Execution

Use this skill when the user asks to execute a large plan safely and incrementally.

## Workflow

1. Normalize scope.
- Convert broad roadmap items into small reversible change-sets.
- Sequence by dependency first, impact second.

2. Enforce change-set template.
- `change_id`
- files touched
- feature flag
- acceptance checks
- rollback steps

3. Execute one change-set only.
- Do not mix unrelated work.
- Keep edits minimal and explicit.

4. Validate before moving on.
- Run targeted tests first.
- Run broader checks if shared surfaces are touched.

5. Log outcomes.
- Record what shipped, what was deferred, and open risks.

## Required Gates

1. Build and typecheck pass.
2. Targeted tests pass.
3. Regression checks for touched diagram families pass.
4. Feature flag rollback verified.

## Prioritization Rule

1. Safety harness and migration prerequisites.
2. High-impact low-risk UX improvements.
3. Parser/export fidelity.
4. New semantic families/features.

