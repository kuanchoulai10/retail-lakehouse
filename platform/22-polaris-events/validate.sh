#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Polaris events pipeline is ready"
log::on_failure "Polaris events pipeline is not ready"

kubectl rollout status deployment/polaris-events-collector \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait \
  --for=condition=Ready kafkatopic/polaris.table.commits \
  --namespace kafka-cdc \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
