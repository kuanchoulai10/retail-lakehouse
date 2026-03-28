#!/bin/bash

set -euo pipefail

CERT_MANAGER_VERSION=v1.18.2
kubectl apply -f "https://github.com/cert-manager/cert-manager/releases/download/$CERT_MANAGER_VERSION/cert-manager.yaml"
