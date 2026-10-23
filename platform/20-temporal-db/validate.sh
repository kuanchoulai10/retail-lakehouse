#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "PostgreSQL for Temporal is ready"
log::on_failure "PostgreSQL for Temporal is not ready"

kubectl rollout status deployment/temporal-db \
  --namespace temporal \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app=temporal-db \
  --namespace temporal \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "$POD" \
  --namespace temporal \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U temporal -d temporal
