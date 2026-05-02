#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating ArgoCD (context: ${KUBE_CONTEXT})"

kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-repo-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-applicationset-controller -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-dex-server -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status deployment/argocd-notifications-controller -n argocd --timeout="${TIMEOUT}"
kubectl --context="${KUBE_CONTEXT}" rollout status statefulset/argocd-application-controller -n argocd --timeout="${TIMEOUT}"

echo ""
echo "==> ArgoCD is ready!"
