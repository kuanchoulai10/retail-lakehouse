#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Spark Operator is ready"
log::on_failure "Spark Operator is not ready"

kubectl rollout status deployment/spark-operator-controller \
  --namespace spark-operator \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/spark-operator-webhook \
  --namespace spark-operator \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
