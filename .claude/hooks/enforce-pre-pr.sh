#!/usr/bin/env bash
# Stop hook: block Claude from stopping if pre-pr checks fail.
# Claude gets sent back to fix the issues.

set -uo pipefail

output=$(task pre-pr 2>&1) || {
  # Extract last 30 lines of failure output for context
  tail_output=$(echo "$output" | tail -30)
  jq -n \
    --arg reason "pre-pr checks failed. Fix the issues and try again." \
    --arg context "$tail_output" \
    '{
      decision: "block",
      reason: $reason,
      hookSpecificOutput: {
        hookEventName: "Stop",
        additionalContext: ("pre-pr output:\n" + $context)
      }
    }'
  exit 2
}
