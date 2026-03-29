#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating ArgoCD root app (context: ${KUBE_CONTEXT})"

kubectl wait application/root-app \
  -n argocd \
  --for=jsonpath='{.status.health.status}'=Healthy \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Root app is Healthy."
