# Table Metrics Prometheus

Wave 26. A small Prometheus in the `table-metrics` namespace (ambient mesh) that keeps the last 6 hours of the table metrics the table maintenance API exports, so the console can draw 1 h, 3 h and 6 h trends. It is separate from the paused `10-kube-prometheus` and is never exposed: no HTTPRoute, only a ClusterIP Service.

## Deployed Resources

```
Namespace: table-metrics
  ConfigMap             table-metrics-prometheus   prometheus.yml
  PersistentVolumeClaim table-metrics-prometheus   2Gi
  Deployment            table-metrics-prometheus   quay.io/prometheus/prometheus:v3.5.0 (Recreate, non-root 65534)
  Service               table-metrics-prometheus   ClusterIP :9090
```

## Scrape

One job, `table-maintenance-api`, scrapes `http://table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000/v1/table-metrics` every 30 s (timeout 10 s). It is one static target (the Service), so several API replicas never duplicate series; every replica reads the same database. Retention is 6 h or 1 GB, whichever comes first.

## Reader

The table maintenance API reads `query_range` from `http://table-metrics-prometheus.table-metrics.svc.cluster.local:9090` (`metrics.prometheusUrl` in the wave 25 chart, rendered as `GLAC_METRICS__PROMETHEUS_URL`). Wave 26 runs after wave 25, which holds the API it scrapes.

## Deploy

```
KUBE_CONTEXT=retail-lakehouse bash platform/26-table-metrics-prometheus/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/26-table-metrics-prometheus/validate.sh
```

`bootstrap.sh` creates the namespace with the ambient label and applies the four manifests. `validate.sh` waits for the rollout, waits up to 120 s for `up{job="table-maintenance-api"}` to be `1`, checks `storage.tsdb.retention.time` is `6h` (both through the API server proxy) and asserts every pod is HBONE.

## Query by hand

```
kubectl port-forward service/table-metrics-prometheus 9090:9090 --namespace table-metrics --context retail-lakehouse
open http://localhost:9090
```
