#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Validating ArgoCD configmap patch (context: ${KUBE_CONTEXT})"

kubectl get configmap argocd-cm -n argocd \
  --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.data.resource\.customizations\.health\.argoproj\.io_Application}' \
  | grep -q "hs.status" || { echo "Patch not found."; exit 1; }
echo "Patch applied."

echo "==> Done."
