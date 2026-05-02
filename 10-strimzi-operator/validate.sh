#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Strimzi Operator is ready"
log::on_failure "Strimzi Operator is not ready"

kubectl rollout status deployment/strimzi-cluster-operator \
  -n strimzi-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
