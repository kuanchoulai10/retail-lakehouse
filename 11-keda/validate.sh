#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating KEDA (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/keda-operator \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/keda-operator-metrics-apiserver \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/keda-admission-webhooks \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> KEDA is ready."
