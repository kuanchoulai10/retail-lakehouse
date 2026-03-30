#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Apache Polaris (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/polaris \
  -n polaris --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Polaris is ready."
