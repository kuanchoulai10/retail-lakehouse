#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating Strimzi Operator"

kubectl rollout status deployment/strimzi-cluster-operator \
  -n strimzi-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::footer "Strimzi Operator is ready"
