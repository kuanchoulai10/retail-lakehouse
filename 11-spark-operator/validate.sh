#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Spark Operator (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/spark-operator-controller \
  -n spark-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/spark-operator-webhook \
  -n spark-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Spark Operator is ready."
