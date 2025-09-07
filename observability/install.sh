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


# Deploy Thanos using kube-thanos jsonnet
# https://github.com/thanos-io/kube-thanos
mkdir -p thanos
cd thanos
jb install github.com/thanos-io/kube-thanos/jsonnet/kube-thanos@main
rm -f manifests/thanos-*
jsonnet -J vendor -m manifests/ thanos.jsonnet | xargs -I{} sh -c "cat {} | yq -P > {}.yaml; rm -f {}" -- {}
