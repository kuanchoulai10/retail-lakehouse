#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
MINIO_POLL_TIMEOUT="${MINIO_POLL_TIMEOUT:-360}"  # seconds to wait for data in MinIO (Iceberg commits every ~5 min)

log::on_success "e2e validation passed: 100 rows inserted into MySQL and data is present in MinIO"
log::on_failure "e2e validation failed"

kubectl wait job/mysql-insert-100-rows \
  --namespace kafka-cdc \
  --for=condition=complete \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

MINIO_USER=$(kubectl get deploy minio \
  --namespace minio \
  --output jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MINIO_ROOT_USER")].value}' \
  --context "${KUBE_CONTEXT}")
MINIO_PASS=$(kubectl get deploy minio \
  --namespace minio \
  --output jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MINIO_ROOT_PASSWORD")].value}' \
  --context "${KUBE_CONTEXT}")

kubectl delete pod mc-e2e-validate \
  --namespace minio \
  --ignore-not-found \
  --context "${KUBE_CONTEXT}" 2>/dev/null || true

# shellcheck disable=SC2016  # vars intentionally unexpanded; they expand inside the container
kubectl run mc-e2e-validate \
  --namespace minio \
  --image minio/mc \
  --restart Never \
  --rm --stdin \
  --env "MINIO_USER=${MINIO_USER}" \
  --env "MINIO_PASS=${MINIO_PASS}" \
  --env "POLL_TIMEOUT=${MINIO_POLL_TIMEOUT}" \
  --context "${KUBE_CONTEXT}" \
  --command -- sh -c '
    mc alias set minio http://minio-api.minio.svc.cluster.local:9000 "$MINIO_USER" "$MINIO_PASS" --quiet
    BASELINE=$(mc ls minio/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null | wc -l | tr -d " ")
    DEADLINE=$(($(date +%s) + $POLL_TIMEOUT))
    while true; do
      COUNT=$(mc ls minio/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null | wc -l | tr -d " ")
      if [ "$COUNT" -gt "$BASELINE" ]; then
        exit 0
      fi
      NOW=$(date +%s)
      if [ "$NOW" -gt "$DEADLINE" ]; then
        exit 1
      fi
      sleep 10
    done
  '
