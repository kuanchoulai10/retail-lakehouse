#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app=polaris-db \
  -n polaris \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Verifying PostgreSQL is accepting connections..."
POD=$(kubectl get pod -l app=polaris-db -n polaris \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n polaris "$POD" --context "${KUBE_CONTEXT}" \
  -- pg_isready -U polaris -d polaris

echo "==> PostgreSQL is ready."
