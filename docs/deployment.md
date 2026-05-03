# Deployment

`task onboard` brings the entire stack up in a single command: the colima VM, the minikube cluster, every app under `platform/`, and the local Python and Node toolchain. This page assumes the tools from [Prerequisites](prerequisites.md) are already installed and walks through the one-shot bootstrap, the deploy-method choice, the layering inside `platform/`, validation, and tear-down.

## Quick start

Pick a name for the kube context (any string; `retail-lakehouse` is the convention used throughout this repo) and run:

```bash
task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts
```

Expect 10 to 20 minutes on first run. When it returns, the cluster is up, every `platform/` app is healthy, and the local dev environment is wired.

## Choose a deploy method

`DEPLOY_METHOD` controls how `platform/` apps land in the cluster. Both end up at the same place; they differ in how you observe and debug the rollout.

| Method | What it does | When to pick it |
|--------|--------------|-----------------|
| `scripts` | Runs each `platform/*/bootstrap.sh` directly in dependency order | Recommended for first-time exploration; failures surface step by step in the terminal |
| `argocd` | Bootstraps Argo CD itself, then applies the `app-of-apps` manifest under `charts/app-of-apps/` | Mirrors a real GitOps workflow and gives you a UI to inspect drift and health |

You can switch methods later by tearing down (`task offboard`) and re-running `task onboard` with the other value.

## What `task onboard` does

`task onboard` is a thin orchestration over three sub-tasks. Knowing what each one does makes failures easier to localise.

### `cluster:bootstrap`: provision the local Kubernetes cluster

The cluster runs inside a colima-managed Linux VM, with minikube on top. The Taskfile defaults are `CPU=9`, `MEMORY=28` (GiB), `DISK_SIZE=120` (GiB), and minikube is given the VM's memory minus 2 GiB so colima itself has room to breathe. Override any of them as Taskfile vars (for example, `task onboard KUBE_CONTEXT=… MEMORY=20`).

The two underlying commands, in case you want to reproduce them by hand or understand what's running on your machine:

```bash title="equivalent of cluster:bootstrap-colima"
colima start \
  --cpu 9 \
  --memory 28 \
  --disk 120 \
  --runtime docker \
  --profile retail-lakehouse
```

```bash title="equivalent of cluster:bootstrap-minikube"
minikube start \
  --profile retail-lakehouse \
  --nodes 1 \
  --cpus 9 \
  --memory 26G \
  --disk-size 120G \
  --driver docker \
  --container-runtime docker \
  --kubernetes-version v1.33.2 \
  --addons registry --addons metrics-server \
  --insecure-registry "10.0.0.0/24" \
  --delete-on-failure
```

`--addons registry` exposes a local container registry so images built inside the project can be pushed without leaving the machine. `metrics-server` enables `kubectl top`. `--insecure-registry "10.0.0.0/24"` permits pushes to that registry over plain HTTP.

![](./assets/k8s-env.excalidraw.svg)
/// caption
K8s Cluster Environment
///

### `apps:bootstrap-by-{scripts|argocd}`: install every app under `platform/`

The selected `DEPLOY_METHOD` decides which sub-task runs. Both walk the `platform/` tree in numeric order (see [Platform layering](#platform-layering) below). The `scripts` path interleaves `bootstrap.sh` and `validate.sh` per tier so a failure stops the cascade early. The `argocd` path hands the whole tree to Argo CD via `app-of-apps` and lets sync waves enforce the same ordering.

### `dev:sync`: local toolchain

Wires the host machine up for development against the running cluster: installs Python deps with `uv`, Node deps with `npm`, and the project's `pre-commit` hooks. Safe to re-run.

## Platform layering

Directories under `platform/` are prefixed with a numeric tier. Lower numbers must be ready before higher numbers. The prefix encodes the dependency order that `bootstrap-by-scripts` walks line by line and that the Argo CD `app-of-apps` encodes via sync waves.

| Prefix | Tier | Examples |
|--------|------|----------|
| `00` to `02` | Argo CD itself (only used when `DEPLOY_METHOD=argocd`) | `00-argocd`, `01-argocd-health-checks`, `02-argocd-apps` |
| `10` | Cluster-wide operators and control planes | `10-cert-manager`, `10-kube-prometheus`, `10-strimzi-operator` |
| `11` | Operators that depend on tier 10 | `11-keda`, `11-spark-operator`, `11-otel-operator` |
| `20` | Stateful infra and standalone services | `20-kafka-cluster`, `20-mysql`, `20-minio`, `20-jaeger-thanos`, `20-jaeger-trino`, `20-polaris-db` |
| `21` | Apps consuming tier-20 services | `21-polaris`, `21-kafka-debezium-mysql-connector` |
| `22` | Apps consuming tier-21 outputs | `22-kafka-iceberg-connector` |
| `23` | Top-level query and UX layer | `23-trino` |
| `25` | Application backend (table maintenance) | `25-tbl-maint-db`, `25-tbl-maint-bcknd`, `25-tbl-maint-schdlr` |
| `30` | Cross-cutting layer above everything | `30-thanos` |

Tier `24-e2e-validation` exists alongside the others and runs end-to-end checks once the upstream tiers are healthy.

## Validate

Once `task onboard` returns, re-run validation any time you want a quick health check:

```bash
task apps:validate KUBE_CONTEXT=retail-lakehouse
```

It runs every `platform/*/validate.sh` in parallel. A non-zero exit means at least one app failed its readiness probe.

## Tear down

To free the resources entirely:

```bash
task offboard KUBE_CONTEXT=retail-lakehouse
```

This deletes the minikube cluster and the colima VM. Both deletes are no-ops if the targets don't exist, so it's safe to re-run.
