#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

log::on_success "Patch applied"
log::on_failure "Patch not applied"

kubectl get configmap argocd-cm \
  --namespace argocd \
  --output jsonpath='{.data.resource\.customizations\.health\.argoproj\.io_Application}' \
  --context "${KUBE_CONTEXT}" \
  | grep -q "hs.status"
