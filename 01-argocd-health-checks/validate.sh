#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

log::header "Validating ArgoCD configmap patch"

kubectl get configmap argocd-cm -n argocd \
  --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.data.resource\.customizations\.health\.argoproj\.io_Application}' \
  | grep -q "hs.status" || log::fail "Patch not found"

log::footer "Patch applied"
