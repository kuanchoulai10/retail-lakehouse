#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Iceberg sink connector deployed"
log::on_failure "Iceberg sink connector deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/iceberg-secret.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/iceberg-connect-cluster.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/iceberg-connector.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
