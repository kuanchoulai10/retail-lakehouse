# Temporal

Deploys the Temporal server with the official `temporalio/temporal` Helm chart (1.7.0) into the `temporal` namespace. Persistence uses the dedicated PostgreSQL from `20-temporal-db` (SQL `postgres12` plugin; databases `temporal` and `temporal_visibility`). The chart's own cassandra / elasticsearch / mysql / postgresql / prometheus / grafana sub-charts do not exist in 1.x, so nothing extra is deployed.

## Versions

| Component | Version |
|-----------|---------|
| Chart `temporalio/temporal` | 1.7.0 |
| `temporalio/server` | 1.32.0 |
| `temporalio/admin-tools` | 1.32.0 |
| `temporalio/ui` | 2.54.1 |

## Deployed Resources

```
Namespace: temporal
├── temporal-frontend / history / matching / worker   (Deployments, 1 replica each)
├── temporal-web                                      (Deployment, Web UI)
├── temporal-admintools                               (Deployment, CLI pod)
└── Helm hook Jobs (schema setup, `default` namespace creation; deleted after success)
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `temporal-frontend.temporal.svc.cluster.local` | 7233 (gRPC), 7243 (HTTP) | Client / worker endpoint |
| `temporal-web.temporal.svc.cluster.local` | 8080 | Web UI (ClusterIP) |

## Sync Wave

Wave 21 — after `20-temporal-db`.

## Schema and Namespace

`createDatabase` and `manageSchema` are enabled for both stores, so the chart's hook Job creates the databases and schemas (idempotent). The `default` Temporal namespace (retention 3 days) is created by the chart's namespace hook Job. `numHistoryShards` is 4 and cannot be changed after the first deployment.

## Installation

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/21-temporal/bootstrap.sh
```

## Validation

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/21-temporal/validate.sh
```

Checks that every Deployment is rolled out, `temporal operator cluster health` reports `SERVING`, and `temporal operator namespace describe default` succeeds.

## Smoke Test

```bash
kubectl exec deployment/temporal-admintools -n temporal --context retail-lakehouse -- \
  temporal workflow start --task-queue smoke-tq --type SmokeWorkflow --workflow-id smoke-1
kubectl exec deployment/temporal-admintools -n temporal --context retail-lakehouse -- temporal workflow list
kubectl exec deployment/temporal-admintools -n temporal --context retail-lakehouse -- \
  temporal workflow terminate --workflow-id smoke-1 --reason done
```

## Web UI

Through `platform-gateway` (HTTPRoute `temporal-web`, path prefix `/temporal`; the UI serves under it through `TEMPORAL_UI_PUBLIC_PATH`):

```bash
kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse
```

Then browse `http://localhost:8591/temporal/`. Directly, without the gateway:

```bash
kubectl port-forward svc/temporal-web 8080:8080 -n temporal --context retail-lakehouse
```
