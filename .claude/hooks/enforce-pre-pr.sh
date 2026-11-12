#!/usr/bin/env bash
# Stop hook: block Claude from stopping if pre-pr checks fail.
# Claude gets sent back to fix the issues.
#
# Skips the gate when the working tree is the one that last passed, and
# otherwise runs only the side (frontend / backend) the change touches.

set -uo pipefail

repo_root="$(git rev-parse --show-toplevel)"
state_file="$(git rev-parse --absolute-git-dir)/pre-pr-last-green-tree"

# The working tree (tracked and untracked, minus ignored files) as one tree id.
working_tree() {
  local index
  index="$(mktemp)"
  rm -f "${index}"
  GIT_INDEX_FILE="${index}" git -C "${repo_root}" read-tree HEAD
  GIT_INDEX_FILE="${index}" git -C "${repo_root}" add -A -- . ':!.claude/worktrees' 2>/dev/null
  GIT_INDEX_FILE="${index}" git -C "${repo_root}" write-tree
  rm -f "${index}"
}

# frontend, backend, all, or none (only paths no test reads: docs, platform, notes).
scope_of() {
  local frontend="" backend="" other="" path
  while IFS= read -r path; do
    case "${path}" in
      src/data-platform/frontend/* | src/design-system/*) frontend=1 ;;
      src/data-platform/backend/* | src/data-platform/runtime/spark/*) backend=1 ;;
      docs/* | platform/* | .scratch/* | .claude/* | *.md) ;;
      *) other=1 ;;
    esac
  done
  if [[ -n "${other}" || (-n "${frontend}" && -n "${backend}") ]]; then
    echo all
  elif [[ -n "${frontend}" ]]; then
    echo frontend
  elif [[ -n "${backend}" ]]; then
    echo backend
  else
    echo none
  fi
}

current="$(working_tree)"
last="$(cat "${state_file}" 2>/dev/null || true)"

if [[ -n "${current}" && "${current}" == "${last}" ]]; then
  exit 0
fi

if [[ -n "${last}" ]] && git -C "${repo_root}" cat-file -e "${last}" 2>/dev/null; then
  scope="$(git -C "${repo_root}" diff --name-only "${last}" "${current}" | scope_of)"
else
  scope=all
fi

if [[ "${scope}" == none ]]; then
  gate=(task gates:pre-commit)
else
  gate=(task gates:pre-pr "scope=${scope}")
fi

output=$("${gate[@]}" 2>&1) || {
  # Extract last 30 lines of failure output for context
  tail_output=$(echo "$output" | tail -30)
  jq -n \
    --arg reason "pre-pr checks failed (${gate[*]}). Fix the issues and try again." \
    --arg context "$tail_output" \
    '{
      continue: false,
      stopReason: ($reason + "\n\n" + $context)
    }'
  exit 0
}

# Hooks in the gate may reformat files, so record the tree as it is now.
passed="$(working_tree)"
[[ -n "${passed}" ]] && echo "${passed}" >"${state_file}"
exit 0
