#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Thanos (context: ${KUBE_CONTEXT})"

kubectl create namespace thanos --context "${KUBE_CONTEXT}" || true

# Render manifests using kube-thanos jsonnet
# https://github.com/thanos-io/kube-thanos
jb install github.com/thanos-io/kube-thanos/jsonnet/kube-thanos@main
rm -f manifests/thanos-*
jsonnet -J vendor -m manifests/ thanos.jsonnet | xargs -I{} sh -c "cat {} | yq -P > {}.yaml; rm -f {}" -- {}

kubectl apply -f manifests/ --context "${KUBE_CONTEXT}"

echo "==> Done."
