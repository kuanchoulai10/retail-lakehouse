#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
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

echo "==> kube-prometheus stack is ready."
