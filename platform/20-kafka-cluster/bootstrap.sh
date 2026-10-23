#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Kafka cluster deployed"
log::on_failure "Kafka cluster deployment failed"

kubectl create namespace kafka \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/kafka-cluster.yaml" \
  --namespace kafka \
  --context "${KUBE_CONTEXT}"
