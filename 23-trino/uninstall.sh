#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling Trino (context: ${KUBE_CONTEXT})"

helm uninstall trino \
  --namespace trino \
  --kube-context "${KUBE_CONTEXT}"

kubectl delete -f "$SCRIPT_DIR/trino-certificate.yaml" \
  --ignore-not-found --context "${KUBE_CONTEXT}"

echo "==> Done."
