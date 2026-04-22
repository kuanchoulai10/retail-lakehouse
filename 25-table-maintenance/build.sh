#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="localhost:5001/table-maintenance-spark:latest"
SPARK_DIR="${SCRIPT_DIR}/../src/table-maintenance/runtime/spark"

echo "==> Building Docker image..."
docker build -t "${IMAGE}" "${SPARK_DIR}"

echo "==> Loading image into Minikube (profile: lakehouse-demo)..."
minikube image load "${IMAGE}" -p lakehouse-demo

echo "==> Image available at ${IMAGE}"
