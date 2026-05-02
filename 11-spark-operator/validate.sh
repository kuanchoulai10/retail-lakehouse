#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Spark Operator is ready"

kubectl rollout status deployment/spark-operator-controller \
  -n spark-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/spark-operator-webhook \
  -n spark-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
