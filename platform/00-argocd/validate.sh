#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "ArgoCD is ready"
log::on_failure "ArgoCD is not ready"

kubectl rollout status deployment/argocd-server \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/argocd-repo-server \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/argocd-applicationset-controller \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/argocd-dex-server \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/argocd-notifications-controller \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status statefulset/argocd-application-controller \
  --namespace argocd \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
