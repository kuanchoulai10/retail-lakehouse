# How the GitOps Deployment Works

This project uses the [App of Apps](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern) pattern with Argo CD. A single root `Application` manages all child `Application` resources declaratively, and Argo CD continuously reconciles the cluster state against what is defined in Git.

## App of Apps Pattern

In this pattern, `argocd/root-app.yaml` is the only resource applied manually. It points Argo CD at a Helm chart (`argocd/chart`) in this repository. That chart does not contain workload manifests. Instead, its templates define Argo CD `Application` and `AppProject` resources, one per component. When Argo CD syncs `root-app`, it renders the Helm chart and creates all child `Application` resources in the cluster. Each child `Application` is then synced independently, deploying the actual workload it describes.

This design keeps every component under GitOps control from a single entry point, with no imperative scripts required after the initial bootstrap.

## Deployment Flow

1. Apply `argocd/root-app.yaml` to the cluster.
2. Argo CD fetches `argocd/chart` from the repository and runs `helm template retail-lakehouse`.
3. The rendered output contains `AppProject` and `Application` manifests. Argo CD applies these to the cluster.
4. Argo CD picks up each child `Application` and syncs them in [sync-wave](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/) order, waiting for each wave to reach **Healthy** before proceeding to the next.

## Sync Wave Order

Each `Application` template carries a `argocd.argoproj.io/sync-wave` annotation that determines its deployment order. The wave assignments reflect the dependency chain between components:

| Wave | Component(s) | Dependency |
|------|-------------|------------|
| 9 | AppProject | Must exist before any `Application` references it |
| 10 | cert-manager, keda, prometheus-operator, spark-operator, strimzi-operator | No intra-project dependencies |
| 11 | opentelemetry-operator | Requires cert-manager (wave 10) for webhook TLS |
| 20 | kafka-cluster, minio, mysql | Requires operators (wave 10) |
| 21 | kafka-debezium-mysql-connector | Requires kafka-cluster and mysql (wave 20) |
| 22 | kafka-iceberg-connector | Requires kafka-debezium-mysql-connector (wave 21) |
| 23 | trino | Requires minio (wave 20) |
| 30 | thanos | Requires prometheus-operator, cert-manager, and opentelemetry-operator |

## Controlling Which Waves Are Deployed

`argocd/chart/values.yaml` exposes a range filter to control which waves are rendered:

```yaml title="argocd/chart/values.yaml"
deploy:
  waveFrom: 9
  waveTo: 10
```

Only `Application` resources with a sync-wave within `[waveFrom, waveTo]` are rendered. Resources outside the range are not created. Updating these values and pushing to `main` is sufficient — Argo CD will re-sync `root-app` and reconcile accordingly.

Common milestones:

| `waveFrom` | `waveTo` | Components deployed |
|-----------|---------|-------------------|
| 9 | 9 | AppProject only |
| 9 | 10 | AppProject + foundation operators |
| 9 | 20 | Above + Kafka, MySQL, MinIO |
| 9 | 30 | Full stack |

## Key Files

| File | Purpose |
|------|---------|
| `argocd/root-app.yaml` | Entry point. Apply once after installing Argo CD. |
| `argocd/chart/values.yaml` | Project name, destination cluster, and wave range. |
| `argocd/chart/templates/` | One file per Application/AppProject, each gated by a wave-range conditional. |
| `argocd/deploy.sh` | Installs Argo CD itself (namespace + upstream manifests). |
| `argocd/validate.sh` | Verifies Argo CD core components are healthy post-install. |
