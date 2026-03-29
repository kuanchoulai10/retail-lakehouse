#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Trino (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/trino-coordinator \
  -n trino --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Trino is ready."
