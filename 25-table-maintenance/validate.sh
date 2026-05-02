#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

log::header "Validating table-maintenance"

log::step "SparkApplication status"
kubectl get sparkapplication table-maintenance-rewrite-data-files -n default \
  -o jsonpath='{.status.applicationState.state}' 2>/dev/null && echo

log::step "MinIO Iceberg data files (inventory.orders)"
kubectl run minio-validate --restart=Never --image=minio/mc --namespace=default \
  --command -- sh -c \
  "mc alias set m http://minio-api.minio.svc.cluster.local:9000 minio_user minio_password \
   && echo '--- data files ---' \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/data/ 2>/dev/null \
   && echo '--- metadata files ---' \
   && mc ls m/retail-lakehouse-7dj2/warehouse/inventory/orders/metadata/ 2>/dev/null \
   && echo '--- totals ---' \
   && mc du m/retail-lakehouse-7dj2/warehouse/inventory/orders/ 2>/dev/null"

kubectl wait --for=condition=ready pod/minio-validate --timeout=60s 2>/dev/null || true
sleep 5
kubectl logs minio-validate 2>/dev/null
kubectl delete pod minio-validate --ignore-not-found 2>/dev/null

log::footer "table-maintenance check done"
