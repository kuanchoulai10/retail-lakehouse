#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating PostgreSQL for table-maintenance"

kubectl wait pod \
  -l app=tbl-maint-db \
  -n default \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

log::step "Verifying PostgreSQL is accepting connections"
kubectl exec -n default \
  "$(kubectl get pod -l app=tbl-maint-db -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U tm -d table_maintenance

log::footer "PostgreSQL is ready"
