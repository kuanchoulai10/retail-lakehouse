#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Strimzi Operator (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/strimzi-cluster-operator \
  -n strimzi-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Strimzi Operator is ready."
