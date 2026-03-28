# How the GitOps Deployment Works

This project uses an **App of Apps** pattern with Argo CD. One root Application manages all other Applications declaratively.

## Overview

```
kubectl apply root-app.yaml
        │
        ▼
┌─────────────────────────────────────────────────┐
│  root-app  (ArgoCD Application)                 │
│  watches: github.com/.../argocd/chart  (Helm)   │
└───────────────────┬─────────────────────────────┘
                    │ renders Helm chart
                    ▼
        ┌───────────────────────┐
        │  argocd/chart/        │
        │  ├── values.yaml      │
        │  └── templates/       │
        │      ├── AppProject   │
        │      ├── cert-manager │
        │      ├── strimzi      │
        │      ├── kafka-cluster│
        │      └── ...          │
        └───────────┬───────────┘
                    │ creates K8s resources (AppProject + Applications)
                    ▼
        ArgoCD syncs each Application
        in sync-wave order
```

## Step-by-Step Flow

### Step 1 — Install Argo CD

```bash
KUBE_CONTEXT=mini bash argocd/deploy.sh
```

Installs the ArgoCD control plane into the `argocd` namespace. Nothing application-specific is deployed yet.

### Step 2 — Apply root-app

```bash
kubectl --context=mini apply -f argocd/root-app.yaml
```

This creates a single ArgoCD `Application` resource called `root-app`. It tells ArgoCD:

- **Watch this repo:** `github.com/kuanchoulai10/retail-lakehouse`
- **Path:** `argocd/chart` (a Helm chart)
- **Render with:** `releaseName: retail-lakehouse` + `valuesObject` overrides
- **Deploy to:** `in-cluster` (the same cluster ArgoCD runs on)

### Step 3 — ArgoCD syncs root-app → renders the Helm chart

ArgoCD fetches `argocd/chart` from the repo and runs `helm template`. The chart's `templates/` contains ArgoCD `Application` and `AppProject` manifests (not your actual workloads). The rendered output is applied to the cluster, creating those resources.

### Step 4 — ArgoCD syncs each Application in sync-wave order

Once the child Applications exist in the cluster, ArgoCD picks them up and syncs them in the order defined by `argocd.argoproj.io/sync-wave` annotations:

| Wave | Resources deployed |
|------|--------------------|
| 9 | `AppProject` (retail-lakehouse) |
| 10 | cert-manager, keda, prometheus-operator, spark-operator, strimzi-operator |
| 11 | opentelemetry-operator *(depends on cert-manager)* |
| 20 | kafka-cluster, minio, mysql |
| 21 | kafka-debezium-mysql-connector *(depends on kafka + mysql)* |
| 22 | kafka-iceberg-connector *(depends on debezium)* |
| 23 | trino *(depends on minio)* |
| 30 | thanos *(depends on prometheus-operator, cert-manager, opentelemetry)* |

ArgoCD waits for each wave to become **Healthy** before starting the next.

## Controlling Which Waves Are Deployed

`argocd/chart/values.yaml` has two fields that act as a range filter:

```yaml
deploy:
  waveFrom: 9
  waveTo: 10
```

Only Applications whose sync-wave falls within `[waveFrom, waveTo]` are rendered by the Helm chart. Waves outside the range are simply not created.

**Examples:**

```bash
# Deploy only operators (waves 9–10)
# → edit values.yaml: waveFrom: 9, waveTo: 10

# Deploy everything
# → edit values.yaml: waveFrom: 9, waveTo: 30

# Deploy up to kafka/minio/mysql only
# → edit values.yaml: waveFrom: 9, waveTo: 20
```

!!! note
    Because `root-app` has `automated.selfHeal: true`, changing `values.yaml` and pushing to `main` is enough — ArgoCD will re-sync automatically and prune Applications that fall outside the new range.

## Key Files

| File | Purpose |
|------|---------|
| `argocd/root-app.yaml` | The single entry-point Application. Apply this after installing ArgoCD. |
| `argocd/chart/values.yaml` | Controls project name, destination cluster, and wave range. |
| `argocd/chart/templates/` | One file per Application/AppProject, each with a sync-wave. |
| `argocd/deploy.sh` | Installs ArgoCD itself (namespace + manifests). |
| `argocd/validate.sh` | Checks all ArgoCD core components are healthy. |
