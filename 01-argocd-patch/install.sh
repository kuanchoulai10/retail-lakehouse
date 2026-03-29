#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Patching ArgoCD configmap (context: ${KUBE_CONTEXT})"

kubectl patch configmap argocd-cm \
  -n argocd \
  --patch-file argocd-cm-patch.yaml \
  --context "${KUBE_CONTEXT}"

echo "==> Done."
