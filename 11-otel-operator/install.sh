#!/bin/bash

set -euo pipefail

OTEL_OPERATOR_VERSION=v0.132.0
kubectl apply -f "https://github.com/open-telemetry/opentelemetry-operator/releases/download/$OTEL_OPERATOR_VERSION/opentelemetry-operator.yaml"
