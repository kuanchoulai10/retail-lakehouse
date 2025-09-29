#!/bin/bash

set -euo pipefail


# Install Prometheus Operator using YAML files
# https://prometheus-operator.dev/docs/getting-started/installation/#install-using-yaml-files
PROMETHEUS_OPERATOR_NAMESPACE=prometheus-operator-system
kubectl create namespace $PROMETHEUS_OPERATOR_NAMESPACE || true
TMPDIR=$(mktemp -d)
PROMETHEUS_OPERATOR_VERSION=v0.85.0
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$PROMETHEUS_OPERATOR_VERSION/kustomization.yaml" > "$TMPDIR/kustomization.yaml"
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$PROMETHEUS_OPERATOR_VERSION/bundle.yaml" > "$TMPDIR/bundle.yaml"
(cd $TMPDIR && kustomize edit set namespace $PROMETHEUS_OPERATOR_NAMESPACE) && kubectl create -k "$TMPDIR"
sleep 5
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=prometheus-operator -n $PROMETHEUS_OPERATOR_NAMESPACE --timeout=180s


# Install Cert-Manager using YAML files
CERT_MANAGER_VERSION=v1.18.2
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/$CERT_MANAGER_VERSION/cert-manager.yaml


# Install OpenTelemetry Operator using YAML files
OTEL_OPERATOR_VERSION=v0.132.0
kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/download/$OTEL_OPERATOR_VERSION/opentelemetry-operator.yaml


cd ~/Projects/retail-lakehouse/thanos
kubectl create namespace thanos || true
# Install Jaeger using Otel Operator
kubectl apply -f manifests/jaeger.yaml -n thanos
# Install Thanos using kube-thanos jsonnet
# https://github.com/thanos-io/kube-thanos
jb install github.com/thanos-io/kube-thanos/jsonnet/kube-thanos@main
rm -f manifests/thanos-*
jsonnet -J vendor -m manifests/ thanos.jsonnet | xargs -I{} sh -c "cat {} | yq -P > {}.yaml; rm -f {}" -- {}
kubectl apply -f manifests/