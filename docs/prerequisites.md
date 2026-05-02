# Prerequisites

For this project, I use a Mac mini (2024) with the following specifications:

- Apple M4 chip
- 10-core CPU
- 10-core GPU
- 16-core Neural Engine
- 32GB RAM
- 512GB SSD

## Installing Required Tools via Homebrew

Make sure you have [Homebrew](https://brew.sh/) installed. Then install the required tools:

```
brew install colima, docker, kubectl, minikube, helm, openjdk@21 jsonnet jsonnet-bundler
```

## Setting Up a Local Kubernetes Cluster

Start colima with more resources:

```bash
colima start \
    --cpu 9 \
    --memory 28 \
    --disk 120 \
    --runtime docker \
    --profile retail-lakehouse
```

This will create a local VM with docker runtime. After installing colima, make sure `docker` uses the colima context (`docker context ls`).

Then start minikube with more resources:

```bash
minikube start \
  --profile retail-lakehouse \
  --nodes 1 \
  --cpus 9 \
  --memory 26G \
  --disk-size 120G \
  --driver docker \
  --container-runtime docker \
  --kubernetes-version v1.33.2 \
  --addons registry --addons metrics-server\
  --insecure-registry "10.0.0.0/24" \
  --delete-on-failure
```

This will create a single-node Kubernetes cluster (9 CPUs, 26GB RAM, 120GB disk) with the local container registry and metrics-server addons enabled. The `--insecure-registry` flag allows pushing images to the local registry; the `metrics-server` addon enables `kubectl top` for nodes and pods.

![](./assets/k8s-env.excalidraw.svg)
///
K8s Cluster Environment
///
