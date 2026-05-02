#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
ARGOCD_VERSION="${ARGOCD_VERSION:-v3.1.7}"

echo "==> Deploying ArgoCD ${ARGOCD_VERSION} (context: ${KUBE_CONTEXT})"

# Create argocd namespace (idempotent)
kubectl --context="${KUBE_CONTEXT}" create namespace argocd --dry-run=client -o yaml \
  | kubectl --context="${KUBE_CONTEXT}" apply -f -

# Install ArgoCD
kubectl --context="${KUBE_CONTEXT}" apply -n argocd \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

echo "==> Done. Run validate.sh to confirm ArgoCD is ready."
