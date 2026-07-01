#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Polaris events pipeline deployed (OTEL collector + Kafka topic)"
log::on_failure "Polaris events pipeline deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/otel-collector.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/kafka-topic.yaml" \
  --context "${KUBE_CONTEXT}"
