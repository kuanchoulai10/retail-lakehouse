#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

echo "==> Removing ArgoCD configmap patch (context: ${KUBE_CONTEXT})"

kubectl patch configmap argocd-cm \
  -n argocd \
  --type=json \
  -p='[{"op": "remove", "path": "/data/resource.customizations.health.argoproj.io~1Application"}]' \
  --context "${KUBE_CONTEXT}"

echo "==> Done."
