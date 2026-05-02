#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::quiet "Polaris is ready"

kubectl rollout status deployment/polaris \
  -n polaris --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
