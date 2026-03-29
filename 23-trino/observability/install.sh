#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

kubectl apply -f "$SCRIPT_DIR/jaeger.yaml"