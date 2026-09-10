#!/bin/bash
# PreToolUse hook — blocks any command that would add a third-party
# dependency to this repo. The project's zero-dependency stance is stated
# in README.md, issue #1 (spec), and implicitly required by every ADR that
# references it. See docs/agent-control.md (once written) and
# docs/agent-control-evidence.md for the skill evidence.

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

if echo "$command" | grep -qE '\b(pip3?|poetry|pipenv)\s+(install|add)\b'; then
    echo "BLOCKED: this repo has a zero-dependency policy (README.md, issue #1). Installing '$command' is not allowed. If the dependency is genuinely needed, this is a project-level decision — raise it with the maintainers, don't add it silently." >&2
    exit 2
fi

exit 0
