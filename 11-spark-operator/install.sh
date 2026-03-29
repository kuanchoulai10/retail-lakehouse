#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Spark Operator 2.3.0 (context: ${KUBE_CONTEXT})"

helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update spark-operator

helm upgrade --install spark-operator spark-operator/spark-operator \
  --version 2.3.0 \
  --namespace spark-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
