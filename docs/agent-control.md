# Agent control

**Instruction — `read-parent-spec` skill.** Tickets in this repo are
deliberately thin; they defer conventions (test framework, file layout,
out-of-scope boundaries) to their parent spec issue rather than restating
them. The skill fires whenever a ticket is implemented, so the agent reads
the full parent issue — not just the ADRs it links to — before writing
code. It should *not* fire on a task with no ticket or spec attached (e.g.
a typo fix); verified in `docs/agent-control-evidence.md`.

**Enforcement — dependency-install hook.** A `PreToolUse` hook blocks any
`pip`/`poetry`/`pipenv install|add` command before it runs, enforcing this
project's zero-dependency stance (stated in the README and issue #1). An
instruction alone was not enough: this exact rule was stated twice during
Lab 1 (at spec time, and again after ticket #2 shipped `pytest` anyway) —
the agent complies most of the time, but the cost of the one time it
doesn't is a dependency silently entering a project that advertises having
none. A floor was worth more than a good compliance rate.
