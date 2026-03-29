#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating cert-manager (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/cert-manager \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/cert-manager-cainjector \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/cert-manager-webhook \
  -n cert-manager --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> cert-manager is ready."
