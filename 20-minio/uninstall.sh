#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deleting MinIO (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/minio.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
