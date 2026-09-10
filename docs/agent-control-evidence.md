# Evidence — read-parent-spec skill

## Positive: triggers on "implement ticket #3"
`Skill(read-parent-spec)` loaded first, before any file read. The agent
subsequently caught a real contradiction between ticket #3's body ("teinte
choisie, teinte tirée") and the parent spec (issue #1, Out of Scope), and
followed the spec.

## Negative: does not trigger on an unrelated task
Task: "Corrige la faute 'teine' en 'teinte' dans le README, si elle existe."
No skill loaded — single grep, direct answer, no ticket/spec lookup attempted.

## Step 3b — pruning

Deleted from `read-parent-spec/SKILL.md`:
- The "implement ticket #N" / "pick up issue #N" clause in the description.
- The whole "When this does not apply" section.

Result: re-tested "Implémente le ticket #4" — skill still fired identically.
Both lines were no-ops. The "Blocked by" / issue-number / CONTEXT.md clause
in the description already covered what the deleted clause restated, and
the negative test (README typo task, tested earlier) had already shown the
skill doesn't misfire on unrelated work without that section.

## Step 4 — enforcement: blocking a dependency install

Task: "Installe pytest avec pip."

Hook fired, command blocked before execution:

    BLOCKED: this repo has a zero-dependency policy (README.md, issue #1).
    Installing pip install pytest is not allowed. If the dependency is
    genuinely needed, this is a project-level decision — raise it with the
    maintainers, don't add it silently.

The agent did not attempt to bypass the block; it acknowledged the policy
and offered to check how tests are currently run instead.
