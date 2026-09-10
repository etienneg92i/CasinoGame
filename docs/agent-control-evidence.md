# Evidence — read-parent-spec skill

## Positive: triggers on "implement ticket #3"
`Skill(read-parent-spec)` loaded first, before any file read. The agent
subsequently caught a real contradiction between ticket #3's body ("teinte
choisie, teinte tirée") and the parent spec (issue #1, Out of Scope), and
followed the spec.

## Negative: does not trigger on an unrelated task
Task: "Corrige la faute 'teine' en 'teinte' dans le README, si elle existe."
No skill loaded — single grep, direct answer, no ticket/spec lookup attempted.
