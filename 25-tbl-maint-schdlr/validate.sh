#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Scheduler is ready"
log::on_failure "Scheduler is not ready"

kubectl rollout status deployment/table-maintenance-scheduler \
  --namespace default \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app=table-maintenance-scheduler \
  --namespace default \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl logs "$POD" \
  --namespace default \
  --tail 5 \
  --context "${KUBE_CONTEXT}" | grep -q "Scheduler tick"
