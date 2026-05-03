#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ARGOCD_VERSION="${ARGOCD_VERSION:-v3.1.7}"

log::on_success "ArgoCD installed"
log::on_failure "ArgoCD installation failed"

# Create argocd namespace (idempotent)
kubectl create namespace argocd \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

# Install ArgoCD
kubectl apply \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml" \
  --namespace argocd \
  --context "${KUBE_CONTEXT}"
