#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
SPARK_OPERATOR_VERSION="${SPARK_OPERATOR_VERSION:-2.3.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Spark Operator ${SPARK_OPERATOR_VERSION} (context: ${KUBE_CONTEXT})"

helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update spark-operator

helm upgrade --install spark-operator spark-operator/spark-operator \
  --version "${SPARK_OPERATOR_VERSION}" \
  --namespace spark-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
