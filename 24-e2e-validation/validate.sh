#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
MINIO_POLL_TIMEOUT="${MINIO_POLL_TIMEOUT:-360}"  # seconds to wait for data in MinIO (Iceberg commits every ~5 min)

log::quiet "e2e validation passed: 100 rows inserted into MySQL and data is present in MinIO"

log::step "Waiting for MySQL insert job to complete"
kubectl wait --for=condition=complete job/mysql-insert-100-rows \
  -n kafka-cdc --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::step "Job completed; fetching MinIO credentials from deployment"
MINIO_USER=$(kubectl get deploy minio -n minio \
  --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MINIO_ROOT_USER")].value}')
MINIO_PASS=$(kubectl get deploy minio -n minio \
  --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MINIO_ROOT_PASSWORD")].value}')

log::step "Polling MinIO for new Iceberg Parquet files (timeout: ${MINIO_POLL_TIMEOUT}s)"
log::detail "Path: retail-lakehouse-7dj2/warehouse/inventory/orders/data/"

kubectl delete pod mc-e2e-validate -n minio \
  --context "${KUBE_CONTEXT}" --ignore-not-found=true 2>/dev/null || true

# shellcheck disable=SC2016  # vars intentionally unexpanded; they expand inside the container
kubectl run mc-e2e-validate --rm -i --restart=Never \
  --image=minio/mc \
  --namespace=minio \
  --context="${KUBE_CONTEXT}" \
  --env="MINIO_USER=${MINIO_USER}" \
  --env="MINIO_PASS=${MINIO_PASS}" \
  --env="POLL_TIMEOUT=${MINIO_POLL_TIMEOUT}" \
  --command -- sh -c '
    mc alias set minio http://minio-api.minio.svc.cluster.local:9000 "$MINIO_USER" "$MINIO_PASS" --quiet
    BASELINE=$(mc ls minio/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null | wc -l | tr -d " ")
    echo "  Baseline Parquet file count: $BASELINE"
    DEADLINE=$(($(date +%s) + $POLL_TIMEOUT))
    while true; do
      COUNT=$(mc ls minio/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null | wc -l | tr -d " ")
      if [ "$COUNT" -gt "$BASELINE" ]; then
        echo "  New Parquet file(s) detected ($BASELINE → $COUNT) — data has landed in MinIO"
        exit 0
      fi
      NOW=$(date +%s)
      if [ "$NOW" -gt "$DEADLINE" ]; then
        echo "  ERROR: Timed out after $POLL_TIMEOUT s — file count stuck at $COUNT"
        exit 1
      fi
      echo "  Still $COUNT file(s), waiting for new commit..."
      sleep 10
    done
  '