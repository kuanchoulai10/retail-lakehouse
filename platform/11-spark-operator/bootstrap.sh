#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
SPARK_OPERATOR_VERSION="${SPARK_OPERATOR_VERSION:-2.3.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Spark Operator installed"
log::on_failure "Spark Operator installation failed"

kubectl create namespace lakehouse-maintenance-operations \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update spark-operator

helm upgrade --install spark-operator spark-operator/spark-operator \
  --version "${SPARK_OPERATOR_VERSION}" \
  --namespace spark-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
