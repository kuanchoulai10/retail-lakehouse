#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

echo "==> Running e2e validation job: insert 100 rows into MySQL (context: ${KUBE_CONTEXT})"

echo "==> Cleaning up previous job run (if any)"
kubectl delete job mysql-insert-100-rows \
  -n kafka-cdc --context "${KUBE_CONTEXT}" --ignore-not-found=true

echo "==> Applying MySQL insert job"
kubectl apply -f "$SCRIPT_DIR/mysql-insert-job.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done. Run validate.sh to verify data flows through to MinIO."
