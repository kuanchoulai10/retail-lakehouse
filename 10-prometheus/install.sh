#!/bin/bash

set -euo pipefail

PROMETHEUS_OPERATOR_NAMESPACE=prometheus-operator-system
kubectl create namespace "$PROMETHEUS_OPERATOR_NAMESPACE" || true
TMPDIR=$(mktemp -d)
PROMETHEUS_OPERATOR_VERSION=v0.85.0
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$PROMETHEUS_OPERATOR_VERSION/kustomization.yaml" > "$TMPDIR/kustomization.yaml"
curl -s "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/refs/tags/$PROMETHEUS_OPERATOR_VERSION/bundle.yaml" > "$TMPDIR/bundle.yaml"
(cd "$TMPDIR" && kustomize edit set namespace "$PROMETHEUS_OPERATOR_NAMESPACE") && kubectl create -k "$TMPDIR"
sleep 5
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=prometheus-operator -n "$PROMETHEUS_OPERATOR_NAMESPACE" --timeout=180s
