#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Patching ArgoCD configmap (context: ${KUBE_CONTEXT})"

kubectl patch configmap argocd-cm \
  -n argocd \
  --patch-file argocd-cm-patch.yaml \
  --context "${KUBE_CONTEXT}"

echo "==> Done."
