#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

kubectl apply -f jaeger.yaml
