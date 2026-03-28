# How the GitOps Deployment Works

If you've just finished installing Argo CD and are wondering *"okay, now what?"* — this page is for you. By the end of it, you'll understand how a single `kubectl apply` command can bootstrap the entire retail-lakehouse stack, and why the architecture is designed this way.

## The Big Picture

Deploying a complex system like this one involves many components — Kafka, MySQL, Trino, MinIO, observability tools — each with its own dependencies. A naive approach might be a long shell script that applies manifests one by one. The problem? It's fragile, hard to observe, and doesn't self-heal when something drifts.

This project takes a different approach: **GitOps with Argo CD**. Instead of running imperative commands, you declare *what* should be running in Git, and Argo CD continuously makes the cluster match that declaration. If someone manually deletes a resource, Argo CD puts it back. If you push a change to the repo, Argo CD applies it automatically.

But there's a bootstrap question: *who manages Argo CD's own Application resources?* You need something to tell Argo CD about all those apps. That's where the **App of Apps** pattern comes in — and it's the heart of how this project works.

## App of Apps in Plain English

Imagine you're opening a new restaurant. You don't just show up and start cooking — you have a *master checklist* that tells your staff what stations to set up, in what order, and what each station needs. The master checklist itself isn't food; it's a plan that produces food.

In Argo CD terms:

- **`root-app.yaml`** is the master checklist — one `Application` resource that points to a Helm chart in this repository.
- That Helm chart **doesn't contain your actual workloads**. It contains definitions of *other Argo CD `Application` resources* — one per component (Kafka, MySQL, Trino, etc.).
- When Argo CD syncs `root-app`, it renders the Helm chart and creates all those child `Application` resources in the cluster.
- Argo CD then picks up each child `Application` and deploys the actual workload it describes.

This is the [App of Apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern). One entry point, fully declarative, and every component under GitOps control from day one.

## The Full Flow, Step by Step

Here's the complete sequence from zero to a running stack:

```
① kubectl apply -f argocd/root-app.yaml
         │
         ▼
② Argo CD syncs root-app
         │  fetches argocd/chart from GitHub
         │  runs: helm template retail-lakehouse argocd/chart
         │
         ▼
③ Helm renders child Application + AppProject manifests
         │  (not workloads — just Argo CD resource definitions)
         │
         ▼
④ Argo CD applies rendered manifests to the cluster
         │  AppProject "retail-lakehouse" created
         │  Application "cert-manager" created
         │  Application "kafka-cluster" created
         │  Application "trino" created
         │  ... and so on
         │
         ▼
⑤ Argo CD syncs each child Application in sync-wave order
         Wave  9 → AppProject
         Wave 10 → cert-manager, keda, prometheus-operator,
                   spark-operator, strimzi-operator
         Wave 11 → opentelemetry-operator
         Wave 20 → kafka-cluster, minio, mysql
         Wave 21 → kafka-debezium-mysql-connector
         Wave 22 → kafka-iceberg-connector
         Wave 23 → trino
         Wave 30 → thanos
```

Steps ②–⑤ happen automatically once `root-app` is applied. You never need to apply the child Applications manually.

### Why a Helm Chart for the App Definitions?

You might wonder: why wrap the `Application` manifests in a Helm chart instead of just keeping plain YAML files? The Helm chart gives us **templating and configurability**. Things like the project name, destination cluster, and — crucially — which waves to deploy, can all be controlled through `values.yaml` without touching every individual file.

### Sync Waves: Enforcing Deployment Order

Argo CD's [sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/) solve the dependency ordering problem. Each `Application` carries an annotation:

```yaml
annotations:
  argocd.argoproj.io/sync-wave: "20"
```

Argo CD waits for all resources in wave N to be **Healthy** before starting wave N+1. This is how we guarantee, for example, that the Strimzi operator (wave 10) is fully ready before the Kafka cluster (wave 20) tries to create its custom resources.

The wave assignments in this project reflect real dependency chains:

| Wave | Component(s) | Why this wave? |
|------|-------------|----------------|
| 9 | AppProject | Must exist before any Application references it |
| 10 | cert-manager, keda, prometheus-operator, spark-operator, strimzi-operator | Foundation operators with no intra-project dependencies |
| 11 | opentelemetry-operator | Requires cert-manager for its webhook TLS certificate |
| 20 | kafka-cluster, minio, mysql | Data layer — depends on operators from wave 10 |
| 21 | kafka-debezium-mysql-connector | CDC capture — needs both Kafka (wave 20) and MySQL (wave 20) |
| 22 | kafka-iceberg-connector | Sink — needs the Debezium source (wave 21) to exist first |
| 23 | trino | Query engine — needs MinIO (wave 20) as its object store |
| 30 | thanos | Observability — depends on prometheus-operator, cert-manager, and opentelemetry |

## Controlling Which Waves Are Deployed

When bootstrapping incrementally — for example, you want to verify operators work before bringing up data services — you don't need to comment out templates. `argocd/chart/values.yaml` exposes a range filter:

```yaml title="argocd/chart/values.yaml"
deploy:
  waveFrom: 9
  waveTo: 10
```

Only Applications whose sync-wave falls within `[waveFrom, waveTo]` are rendered by the Helm chart. The rest simply don't exist in the cluster. When you're ready to extend, bump `waveTo` and push — Argo CD will self-heal `root-app` and create the new Applications automatically.

Some useful milestones:

| `waveFrom` | `waveTo` | What gets deployed |
|-----------|---------|-------------------|
| 9 | 9 | AppProject only |
| 9 | 10 | AppProject + all foundation operators |
| 9 | 20 | Everything above + Kafka, MySQL, MinIO |
| 9 | 30 | The full stack |

## Key Files at a Glance

| File | What it is |
|------|-----------|
| `argocd/root-app.yaml` | The single entry-point. Apply this once after installing Argo CD. |
| `argocd/chart/values.yaml` | Tune project name, destination cluster, and wave range here. |
| `argocd/chart/templates/` | One file per Application/AppProject. Each wraps its content in a wave-range conditional. |
| `argocd/deploy.sh` | Installs Argo CD itself (namespace + upstream manifests). |
| `argocd/validate.sh` | Verifies all Argo CD core components rolled out successfully. |
