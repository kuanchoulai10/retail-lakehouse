#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <org/repo>"
  echo ""
  echo "List all tags for a GitHub repository with their corresponding commit SHAs,"
  echo "sorted from newest to oldest."
  echo ""
  echo "Useful for pinning pre-commit hook revisions to a specific commit SHA"
  echo "instead of a mutable tag reference."
  echo ""
  echo "Requirements: gh (GitHub CLI), authenticated via 'gh auth login'"
  echo ""
  echo "Example:"
  echo "  $0 gitleaks/gitleaks"
  echo ""
  echo "Output:"
  echo "  83d9cd684c87d95d656c1458ef04895a7f1cbd8e  v8.30.1"
  echo "  6eaad039603a4de39fddd1cf5f727391efe9974e  v8.30.0"
  echo "  ..."
  exit 1
}

[[ $# -ne 1 || "$1" == "--help" || "$1" == "-h" ]] && usage

ORG_REPO="$1"

gh api "repos/${ORG_REPO}/tags" \
  --paginate \
  --jq '.[] | "\(.commit.sha)  \(.name)"'
