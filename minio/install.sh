#!/bin/bash

set -euo pipefail

kubectl create namespace minio
kubectl apply -f minio.yaml
