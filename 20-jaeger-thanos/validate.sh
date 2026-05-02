#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Jaeger (thanos) is ready"
log::on_failure "Jaeger (thanos) is not ready"

kubectl wait pod \
  --selector app.kubernetes.io/managed-by=opentelemetry-operator \
  --namespace thanos \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
