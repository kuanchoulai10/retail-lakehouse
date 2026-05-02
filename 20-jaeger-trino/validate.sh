#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Jaeger (trino) is ready"
log::on_failure "Jaeger (trino) is not ready"

kubectl wait pod \
  --selector app.kubernetes.io/managed-by=opentelemetry-operator \
  --namespace trino \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
