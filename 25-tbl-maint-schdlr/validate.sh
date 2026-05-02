#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::quiet "Scheduler is ready"

kubectl rollout status deployment/table-maintenance-scheduler \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::step "Checking scheduler logs for tick output"
POD=$(kubectl get pod -l app=table-maintenance-scheduler -n default \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$POD" -n default --context "${KUBE_CONTEXT}" --tail=5 | grep -q "Scheduler tick"