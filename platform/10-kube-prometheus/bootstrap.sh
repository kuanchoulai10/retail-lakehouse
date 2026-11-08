#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
KUBE_PROMETHEUS_VERSION="${KUBE_PROMETHEUS_VERSION:-v0.17.0}"
KUBE_PROMETHEUS_SHA="${KUBE_PROMETHEUS_SHA:-d6d094d115093d81d3355bc970a93e4357d6ef05}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "kube-prometheus installed"
log::on_failure "kube-prometheus installation failed"

rm -rf kube-prometheus
git clone \
  --depth 1 \
  --branch "${KUBE_PROMETHEUS_VERSION}" \
  https://github.com/prometheus-operator/kube-prometheus.git

actual_sha=$(git -C kube-prometheus rev-parse HEAD)
if [ "$actual_sha" != "$KUBE_PROMETHEUS_SHA" ]; then
  echo "SHA mismatch! expected ${KUBE_PROMETHEUS_SHA}, got ${actual_sha}" >&2
  rm -rf kube-prometheus
  exit 1
fi

# Single-node dev cluster: scrape the /metrics/slis endpoints every 30s
# instead of 5s, and drop the high-cardinality apiserver and etcd histograms
# that no upstream rule or dashboard reads. The SLI histogram stays because
# the apiserver burn-rate rules use it.
for service_monitor in Apiserver Kubelet; do
  yq -i \
    '(.spec.endpoints[] | select(.path == "/metrics/slis")).interval = "30s"' \
    "kube-prometheus/manifests/kubernetesControlPlane-serviceMonitor${service_monitor}.yaml"
done
yq -i \
  '(.spec.endpoints[] | select(.path == null)).metricRelabelings += [{
    "action": "drop",
    "regex": "(apiserver_request_duration_seconds|etcd_request_duration_seconds|apiserver_request_body_size_bytes|apiserver_response_sizes)_bucket",
    "sourceLabels": ["__name__"]
  }]' \
  kube-prometheus/manifests/kubernetesControlPlane-serviceMonitorApiserver.yaml

kubectl apply \
  --server-side \
  --force-conflicts \
  -f kube-prometheus/manifests/setup \
  --context "${KUBE_CONTEXT}"

until kubectl get servicemonitors \
  --all-namespaces \
  --context "${KUBE_CONTEXT}" 2>/dev/null; do
  sleep 1
done

kubectl apply \
  --server-side \
  --force-conflicts \
  -f kube-prometheus/manifests/ \
  --context "${KUBE_CONTEXT}"

# Single-node minikube dev cluster: upstream HA defaults waste CPU/RAM.
# Server-side apply with a dedicated field manager so we co-own only the
# fields in dev-overrides.yaml and the operator keeps owning the rest.
kubectl apply \
  --server-side \
  --field-manager=dev-overrides \
  --force-conflicts \
  -f "$SCRIPT_DIR/dev-overrides.yaml" \
  --context "${KUBE_CONTEXT}"

rm -rf kube-prometheus
