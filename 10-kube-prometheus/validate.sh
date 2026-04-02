#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating kube-prometheus stack (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/prometheus-operator \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/grafana \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/kube-state-metrics \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/prometheus-adapter \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/blackbox-exporter \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status statefulset/prometheus-k8s \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status statefulset/alertmanager-main \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status daemonset/node-exporter \
  -n monitoring --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Validating Prometheus RBAC for trino namespace"
kubectl auth can-i list services \
  --as=system:serviceaccount:monitoring:prometheus-k8s \
  -n trino --context "${KUBE_CONTEXT}" | grep -q "^yes$"

echo "==> Validating Prometheus is scraping Trino targets"
TRINO_TARGETS=$(kubectl exec -n monitoring prometheus-k8s-0 --context "${KUBE_CONTEXT}" -- \
  wget -qO- 'http://localhost:9090/api/v1/targets' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
up = [t for t in data['data']['activeTargets']
      if 'trino' in t.get('scrapePool','') and t.get('health') == 'up']
print(len(up))
")
if [ "${TRINO_TARGETS}" -lt 1 ]; then
  echo "ERROR: No healthy Trino targets found in Prometheus"
  exit 1
fi
echo "  Found ${TRINO_TARGETS} healthy Trino target(s)"

echo "==> kube-prometheus stack is ready."
