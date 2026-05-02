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
