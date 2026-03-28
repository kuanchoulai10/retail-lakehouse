#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

kubectl create namespace thanos || true

# Install Jaeger using Otel Operator
kubectl apply -f manifests/jaeger.yaml -n thanos

# Install Thanos using kube-thanos jsonnet
# https://github.com/thanos-io/kube-thanos
jb install github.com/thanos-io/kube-thanos/jsonnet/kube-thanos@main
rm -f manifests/thanos-*
jsonnet -J vendor -m manifests/ thanos.jsonnet | xargs -I{} sh -c "cat {} | yq -P > {}.yaml; rm -f {}" -- {}
kubectl apply -f manifests/
