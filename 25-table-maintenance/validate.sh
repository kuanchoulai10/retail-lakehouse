#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

log::on_success "table-maintenance check done"
log::on_failure "table-maintenance check failed"

kubectl get sparkapplication table-maintenance-rewrite-data-files \
  --namespace default \
  --output jsonpath='{.status.applicationState.state}' \
  --context "${KUBE_CONTEXT}" 2>/dev/null

kubectl run minio-validate \
  --namespace default \
  --image minio/mc \
  --restart Never \
  --context "${KUBE_CONTEXT}" \
  --command -- sh -c \
  "mc alias set m http://minio-api.minio.svc.cluster.local:9000 minio_user minio_password \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/metadata/ 2>/dev/null \
   && mc du m/retail-lakehouse-7dj2/warehouse/inventory/orders/ 2>/dev/null"

kubectl wait pod/minio-validate \
  --namespace default \
  --for=condition=ready \
  --timeout 60s \
  --context "${KUBE_CONTEXT}" 2>/dev/null || true
sleep 5
kubectl logs minio-validate \
  --namespace default \
  --context "${KUBE_CONTEXT}" 2>/dev/null
kubectl delete pod minio-validate \
  --namespace default \
  --ignore-not-found \
  --context "${KUBE_CONTEXT}" 2>/dev/null
