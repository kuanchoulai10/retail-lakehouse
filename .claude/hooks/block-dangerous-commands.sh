#!/usr/bin/env bash
# PreToolUse hook: block dangerous shell commands.

set -euo pipefail

cmd=$(jq -r '.tool_input.command // empty')
blocked=""

# --- cd: always use absolute paths instead ---
if echo "$cmd" | grep -qE '(^|[;&|]\s*)cd\s'; then
  blocked="cd (use absolute paths instead)"
fi

# --- Destructive file operations ---
[[ "$cmd" == *"rm -rf"* ]] && blocked="rm -rf"

# --- Python: must use uv run ---
if echo "$cmd" | grep -qE '^\s*(python3?|pytest|pip)\b' && ! echo "$cmd" | grep -qE '^\s*uv run\b'; then
  blocked="bare python/pytest/pip (use 'uv run' instead)"
fi

# --- Minikube: destructive ---
[[ "$cmd" == *"minikube delete"* ]] && blocked="minikube delete"

# --- Output deny decision if blocked ---
if [[ -n "$blocked" ]]; then
  jq -n \
    --arg reason "Blocked: $blocked." \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
fi
