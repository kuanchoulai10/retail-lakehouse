#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deleting MinIO (context: ${KUBE_CONTEXT})"

kubectl delete -f minio.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
