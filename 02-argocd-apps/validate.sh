#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating ArgoCD root app"

kubectl wait application/root-app \
  -n argocd \
  --for=jsonpath='{.status.health.status}'=Healthy \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

log::footer "Root app is Healthy"
