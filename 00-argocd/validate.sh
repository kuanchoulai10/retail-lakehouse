#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating ArgoCD"

kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-repo-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-applicationset-controller -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-dex-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-notifications-controller -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status statefulset/argocd-application-controller -n argocd --timeout="${TIMEOUT}"

log::footer "ArgoCD is ready"
