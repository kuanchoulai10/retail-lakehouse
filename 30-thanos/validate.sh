#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating Thanos"

kubectl rollout status deployment/thanos-query \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/thanos-query-frontend \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/thanos-receive-router \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::footer "Thanos is ready"
