#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="localhost:5000/table-maintenance-jobs:latest"
JOBS_DIR="${SCRIPT_DIR}/../src/table-maintenance/jobs"

echo "==> Building Docker image..."
docker build -t "${IMAGE}" "${JOBS_DIR}"

echo "==> Loading image into Minikube (profile: lakehouse-demo)..."
minikube image load "${IMAGE}" -p lakehouse-demo

echo "==> Image available at ${IMAGE}"
