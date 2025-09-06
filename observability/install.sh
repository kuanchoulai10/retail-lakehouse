#!/bin/bash

set -euo pipefail

NAMESPACE=observability

kubectl create namespace $NAMESPACE || true

# Install Prometheus Operator using YAML files
# https://prometheus-operator.dev/docs/getting-started/installation/#install-using-yaml-files
TMPDIR=$(mktemp -d)
LATEST=v0.85.0
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$LATEST/kustomization.yaml" > "$TMPDIR/kustomization.yaml"
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$LATEST/bundle.yaml" > "$TMPDIR/bundle.yaml"
(cd $TMPDIR && kustomize edit set namespace $NAMESPACE) && kubectl create -k "$TMPDIR"
sleep 5
kubectl wait --for=condition=Ready pods -l  app.kubernetes.io/name=prometheus-operator -n $NAMESPACE --timeout=180s

# Deploy a Thanos using Bitnami Helm Chart
# https://artifacthub.io/packages/helm/bitnami/thanos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
