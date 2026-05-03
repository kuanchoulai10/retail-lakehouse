# Deployment

`task onboard` brings the entire stack up in a single command: the colima VM, the minikube cluster, every app under `platform/`, and the local Python and Node toolchain. This page assumes the tools from [Prerequisites](prerequisites.md) are already installed.

## Quick start

Pick a name for the kube context (any string; `retail-lakehouse` is the convention used throughout this repo) and run:

```bash
task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts
```

Expect 10 to 20 minutes on first run. When it returns, the cluster is up, every `platform/` app is healthy, and the local dev environment is wired.

## What `task onboard` does

`task onboard` is a thin orchestration over three steps:

1. **Provision the cluster.** Boots a colima VM and starts a minikube cluster on top of it.
2. **Install the platform.** Walks every directory under `platform/` in dependency order and applies it to the cluster.
3. **Set up the local toolchain.** Installs Python deps with `uv`, Node deps with `npm`, and the project's `pre-commit` hooks.

`DEPLOY_METHOD` controls how step 2 is performed:

| Method | What it does | When to pick it |
|--------|--------------|-----------------|
| `scripts` | Runs each `platform/*/bootstrap.sh` directly in dependency order | Recommended for first-time exploration; failures surface step by step in the terminal |
| `argocd` | Bootstraps Argo CD itself, then applies the `app-of-apps` manifest under `charts/app-of-apps/` | Mirrors a real GitOps workflow and gives you a UI to inspect drift and health |

You can switch methods later by tearing down (`task offboard`) and re-running `task onboard` with the other value.

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
