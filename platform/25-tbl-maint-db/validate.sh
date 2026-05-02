#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "PostgreSQL for table-maintenance is ready"
log::on_failure "PostgreSQL for table-maintenance is not ready"

kubectl rollout status deployment/tbl-maint-db \
  --namespace default \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app=tbl-maint-db \
  --namespace default \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "$POD" \
  --namespace default \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U tm -d table_maintenance
