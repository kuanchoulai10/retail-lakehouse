#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Jaeger for Trino installed"
log::on_failure "Jaeger for Trino installation failed"

namespace::apply_ambient lakehouse-query-engine

kubectl apply \
  -f "$SCRIPT_DIR/jaeger.yaml" \
  --namespace lakehouse-query-engine \
  --context "${KUBE_CONTEXT}"
