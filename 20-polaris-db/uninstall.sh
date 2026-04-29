#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"
echo "    NOTE: PVC 'polaris-db' is intentionally NOT deleted to prevent data loss."
echo "    To remove data: kubectl delete pvc polaris-db -n polaris --context ${KUBE_CONTEXT}"

kubectl delete -f "$SCRIPT_DIR/polaris-db-service.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found
kubectl delete -f "$SCRIPT_DIR/polaris-db-deployment.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found
kubectl delete -f "$SCRIPT_DIR/polaris-db-secret.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found

echo "==> Done."
