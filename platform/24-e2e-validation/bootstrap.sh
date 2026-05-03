#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

log::on_success "MySQL insert job submitted"
log::on_failure "MySQL insert job submission failed"

kubectl delete job mysql-insert-100-rows \
  --namespace kafka-cdc \
  --ignore-not-found=true \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/mysql-insert-job.yaml" \
  --context "${KUBE_CONTEXT}"
