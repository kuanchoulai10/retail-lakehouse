#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating PostgreSQL for table-maintenance (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app=tbl-maint-db \
  -n default \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Verifying PostgreSQL is accepting connections..."
kubectl exec -n default \
  "$(kubectl get pod -l app=tbl-maint-db -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U tm -d table_maintenance

echo "==> PostgreSQL is ready."
