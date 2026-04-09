#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Submitting table-maintenance rewrite-data-files job..."
kubectl apply -f "${SCRIPT_DIR}/sparkapplication-rewrite-data-files.yaml"

echo "==> Waiting for SparkApplication to start..."
kubectl wait sparkapplication/table-maintenance-rewrite-data-files \
  --for=condition=Running \
  --timeout=120s \
  --namespace=default 2>/dev/null || true

echo "==> SparkApplication submitted. Check status with:"
echo "    kubectl get sparkapplication table-maintenance-rewrite-data-files -n default"
echo "    kubectl logs -n default -l spark-role=driver,spark-app-name=table-maintenance-rewrite-data-files -f"
