#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Kafbat UI deployed"
log::on_failure "Kafbat UI deployment failed"

namespace::apply_ambient kafka-ui

kubectl apply \
  -f "$SCRIPT_DIR/kafka-ui-configmap.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/kafka-ui-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/kafka-ui-service.yaml" \
  --context "${KUBE_CONTEXT}"

gateway::allow_routes kafka-ui
kubectl apply \
  -f "$SCRIPT_DIR/kafka-ui-route.yaml" \
  --context "${KUBE_CONTEXT}"
