#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Thanos (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/thanos-query \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/thanos-query-frontend \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/thanos-receive-router \
  -n thanos --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Thanos is ready."
