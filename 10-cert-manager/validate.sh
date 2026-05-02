#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating cert-manager"

kubectl rollout status deployment/cert-manager \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/cert-manager-cainjector \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/cert-manager-webhook \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::footer "cert-manager is ready"
