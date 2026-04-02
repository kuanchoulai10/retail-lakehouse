#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Trino (context: ${KUBE_CONTEXT})"

kubectl wait --for=condition=Ready certificate/trino-tls \
  -n trino --timeout=60s --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-coordinator \
  -n trino --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-worker \
  -n trino --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Validating JMX exporter sidecar is running"
CONTAINERS=$(kubectl get deployment/trino-coordinator -n trino --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.spec.template.spec.containers[*].name}' | tr ' ' '\n' | wc -l | tr -d ' ')
if [ "${CONTAINERS}" -lt 2 ]; then
  echo "ERROR: JMX exporter sidecar not found in coordinator (expected 2 containers)"
  exit 1
fi

echo "==> Validating ServiceMonitor exists"
kubectl get servicemonitor trino -n trino --context "${KUBE_CONTEXT}" > /dev/null
kubectl get servicemonitor trino-worker -n trino --context "${KUBE_CONTEXT}" > /dev/null

echo "==> Trino is ready."
