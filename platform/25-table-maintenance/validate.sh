#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-120s}"

log::on_success "table-maintenance check done"
log::on_failure "table-maintenance check failed"

kubectl wait sparkapplication/table-maintenance-rewrite-data-files \
  --for=condition=Running \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}" 2>/dev/null || true

kubectl get sparkapplication table-maintenance-rewrite-data-files \
  --namespace polaris \
  --output jsonpath='{.status.applicationState.state}' \
  --context "${KUBE_CONTEXT}" 2>/dev/null

kubectl run minio-validate \
  --namespace polaris \
  --image minio/mc \
  --restart Never \
  --context "${KUBE_CONTEXT}" \
  --command -- sh -c \
  "mc alias set m http://minio-api.minio.svc.cluster.local:9000 minio_user minio_password \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/metadata/ 2>/dev/null \
   && mc du m/retail-lakehouse-7dj2/warehouse/inventory/orders/ 2>/dev/null"

kubectl wait pod/minio-validate \
  --namespace polaris \
  --for=condition=ready \
  --timeout 60s \
  --context "${KUBE_CONTEXT}" 2>/dev/null || true
sleep 5
kubectl logs minio-validate \
  --namespace polaris \
  --context "${KUBE_CONTEXT}" 2>/dev/null
kubectl delete pod minio-validate \
  --namespace polaris \
  --ignore-not-found \
  --context "${KUBE_CONTEXT}" 2>/dev/null
