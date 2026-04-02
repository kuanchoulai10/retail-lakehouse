#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
KUBE_PROMETHEUS_VERSION="${KUBE_PROMETHEUS_VERSION:-v0.17.0}"
KUBE_PROMETHEUS_SHA="${KUBE_PROMETHEUS_SHA:-d6d094d115093d81d3355bc970a93e4357d6ef05}"

echo "==> Cloning kube-prometheus ${KUBE_PROMETHEUS_VERSION} (context: ${KUBE_CONTEXT})"

git clone --depth 1 --branch "${KUBE_PROMETHEUS_VERSION}" \
  https://github.com/prometheus-operator/kube-prometheus.git

actual_sha=$(git -C kube-prometheus rev-parse HEAD)
if [ "$actual_sha" != "$KUBE_PROMETHEUS_SHA" ]; then
  echo "SHA mismatch! expected ${KUBE_PROMETHEUS_SHA}, got ${actual_sha}"
  rm -rf kube-prometheus
  exit 1
fi

echo "==> Installing namespace and CRDs"
kubectl create -f kube-prometheus/manifests/setup --context "${KUBE_CONTEXT}"

echo "==> Waiting for servicemonitors CRD"
until kubectl get servicemonitors --all-namespaces --context "${KUBE_CONTEXT}" 2>/dev/null; do
  date; sleep 1; echo ""
done

echo "==> Installing remaining resources"
kubectl create -f kube-prometheus/manifests/ --context "${KUBE_CONTEXT}"

echo "==> Cleaning up"
rm -rf kube-prometheus

echo "==> Applying Prometheus RBAC for additional namespaces"
kubectl apply -f "$SCRIPT_DIR/prometheus-rolebinding-trino.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
