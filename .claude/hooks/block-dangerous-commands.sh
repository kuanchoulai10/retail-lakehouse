#!/usr/bin/env bash
# PreToolUse hook: block dangerous shell commands.
# Principle: build manifests → kubectl apply, don't mutate cluster directly.

set -euo pipefail

cmd=$(jq -r '.tool_input.command // empty')
blocked=""

# --- cd: always use absolute paths instead ---
if echo "$cmd" | grep -qE '(^|[;&|]\s*)cd\s'; then
  blocked="cd (use absolute paths instead)"
fi

# --- Destructive file operations ---
[[ "$cmd" == *"rm -rf"* ]] && blocked="rm -rf"

# --- kubectl: leading flags before verb (e.g. `kubectl -n ns get pods`).
# Use `kubectl <verb> <flags>` form instead (e.g. `kubectl get -n ns pods`).
# Verb-first matches the existing permission allow-list (Bash(kubectl get:*) etc.),
# so flag-first commands trigger an interactive permission prompt every time. ---
if echo "$cmd" | grep -qE '\bkubectl[[:space:]]+-'; then
  blocked="kubectl with leading flags (put verb first: 'kubectl get -n NS pods' not 'kubectl -n NS get pods')"
fi

# --- kubectl: direct cluster mutation ---
[[ "$cmd" == *"kubectl delete"* ]]   && blocked="kubectl delete"
[[ "$cmd" == *"kubectl edit"* ]]     && blocked="kubectl edit"
[[ "$cmd" == *"kubectl set "* ]]     && blocked="kubectl set"
[[ "$cmd" == *"kubectl scale"* ]]    && blocked="kubectl scale"
[[ "$cmd" == *"kubectl cordon"* ]]   && blocked="kubectl cordon"
[[ "$cmd" == *"kubectl drain"* ]]    && blocked="kubectl drain"
[[ "$cmd" == *"kubectl taint"* ]]    && blocked="kubectl taint"
[[ "$cmd" == *"kubectl label"* ]]    && blocked="kubectl label"
[[ "$cmd" == *"kubectl annotate"* ]] && blocked="kubectl annotate"
[[ "$cmd" == *"kubectl replace"* ]]  && blocked="kubectl replace"

# --- kubectl patch: allowed only with -f / --filename ---
if [[ "$cmd" == *"kubectl patch"* ]] && ! echo "$cmd" | grep -qE '\-f\b|--filename'; then
  blocked="kubectl patch (without -f)"
fi

# --- Python: must use uv run ---
if echo "$cmd" | grep -qE '^\s*(python3?|pytest|pip)\b' && ! echo "$cmd" | grep -qE '^\s*uv run\b'; then
  blocked="bare python/pytest/pip (use 'uv run' instead)"
fi

# --- Minikube: destructive ---
[[ "$cmd" == *"minikube delete"* ]] && blocked="minikube delete"

# --- Output deny decision if blocked ---
if [[ -n "$blocked" ]]; then
  jq -n \
    --arg reason "Blocked: $blocked. Use manifests + kubectl apply instead." \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
fi
