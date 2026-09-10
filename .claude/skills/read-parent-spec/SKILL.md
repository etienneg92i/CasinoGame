---
name: read-parent-spec
description: Use before implementing any ticket/issue in this repo that references a parent spec issue (a "Blocked by" link, an explicit issue number, or a mention of CONTEXT.md/ADRs). Also use whenever asked to "implement ticket #N" or "pick up issue #N" directly — tickets in this repo are intentionally short and defer conventions to their parent spec rather than restating them.
---

# Read the parent spec before implementing

Tickets in this repo are deliberately thin. They describe *what* to build, not
the project-wide conventions (test framework, file layout, out-of-scope
boundaries) — those live once, in the parent spec issue, not copy-pasted into
every ticket.

## Do this, in order, before writing any code

1. Find the parent spec issue number (the ticket's "Blocked by" field, or a
   direct reference in its body).
2. `gh issue view <parent> --repo <owner>/<repo>` and read the **full body** —
   not just the ADRs or CONTEXT.md it links to. Pay particular attention to
   any "Testing Decisions", "Implementation Decisions", and "Out of Scope"
   sections: these are usually not restated per-ticket.
3. Note, before implementing, which of those constraints apply to *this*
   ticket specifically.

## Done when

- You can state, without re-opening the issue, the test framework, the test
  file location, and at least one out-of-scope item from the parent spec.
- Every test file you create matches that framework and location — verified
  by actually running the command the spec names (e.g. `python -m unittest`),
  not by assuming.

## When this does not apply

A ticket with no parent spec issue — a standalone bugfix or chore with
nothing to inherit — does not need this lookup.
