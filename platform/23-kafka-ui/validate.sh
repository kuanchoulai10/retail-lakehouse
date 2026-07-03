#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Kafbat UI is ready"
log::on_failure "Kafbat UI is not ready"

kubectl rollout status deployment/kafka-ui \
  --namespace kafka-ui \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
