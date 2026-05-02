#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="localhost:5001/table-maintenance-spark:latest"
SPARK_DIR="${SCRIPT_DIR}/../src/table-maintenance/runtime/spark"

echo "==> Building Docker image..."
docker build -t "${IMAGE}" "${SPARK_DIR}"

echo "==> Loading image into Minikube (profile: ${KUBE_CONTEXT})..."
minikube image load "${IMAGE}" -p "${KUBE_CONTEXT}"

echo "==> Image available at ${IMAGE}"
