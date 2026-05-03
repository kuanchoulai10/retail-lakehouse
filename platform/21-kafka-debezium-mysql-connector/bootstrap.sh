#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Debezium MySQL connector deployed"
log::on_failure "Debezium MySQL connector deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/debezium-secret.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-role.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-role-binding.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-connect-cluster.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-connector.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
