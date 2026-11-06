#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "kube-prometheus stack is ready"
log::on_failure "kube-prometheus stack is not ready"

kubectl rollout status deployment/prometheus-operator \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/grafana \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/kube-state-metrics \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/prometheus-adapter \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/blackbox-exporter \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status statefulset/prometheus-k8s \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status statefulset/alertmanager-main \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status daemonset/node-exporter \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

expected_resources='{"limits":{"memory":"1Gi"},"requests":{"cpu":"100m","memory":"400Mi"}}'
for _ in $(seq 1 30); do
  prometheus_resources=$(kubectl get statefulset prometheus-k8s \
    --output jsonpath='{.spec.template.spec.containers[?(@.name=="prometheus")].resources}' \
    --namespace monitoring \
    --context "${KUBE_CONTEXT}")
  if [ "$(jq --compact-output --sort-keys . <<<"${prometheus_resources}")" = "${expected_resources}" ]; then
    break
  fi
  sleep 2
done
if [ "$(jq --compact-output --sort-keys . <<<"${prometheus_resources}")" != "${expected_resources}" ]; then
  echo "prometheus container resources are ${prometheus_resources}, expected ${expected_resources}" >&2
  exit 1
fi

kubectl rollout status statefulset/prometheus-k8s \
  --namespace monitoring \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
