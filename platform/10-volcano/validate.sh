#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Volcano is ready"
log::on_failure "Volcano is not ready"

kubectl rollout status deployment/volcano-admission \
  --namespace volcano-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/volcano-controllers \
  --namespace volcano-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/volcano-scheduler \
  --namespace volcano-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait queue/default \
  --for=jsonpath='{.status.state}'=Open \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
