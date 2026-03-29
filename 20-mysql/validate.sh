#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating MySQL (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app=mysql \
  -n kafka-cdc \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> MySQL is ready."
