# Thanos

Deploys Thanos, a highly available Prometheus extension, using jsonnet-generated manifests. Thanos provides long-term metrics storage by shipping Prometheus data to MinIO, and enables global query across multiple Prometheus instances. This deployment includes the full Thanos component set.

## Deployed Resources

```
Namespace: thanos
├── thanos-query                         (Deployment)
├── thanos-query-frontend                (Deployment)
├── thanos-receive-router                (Deployment)
├── thanos-receive-ingestor-default      (StatefulSet)
├── thanos-compact-shard{0,1,2}          (StatefulSet)
├── thanos-store-shard{0,1,2}            (StatefulSet)
├── thanos-bucket-web                    (Deployment)
├── thanos-ruler                         (StatefulSet)
└── memcached                            (StatefulSet)
```

## Namespaces

- `thanos`

## Pods

| Pod | Purpose |
|-----|---------|
| `thanos-query` | Executes PromQL queries across all Thanos stores |
| `thanos-query-frontend` | Caches and shards queries for the query layer |
| `thanos-receive-router` | Routes incoming remote write requests to ingestors |
| `thanos-receive-ingestor-default` | Receives and stores incoming metrics |
| `thanos-compact-shard{0,1,2}` | Compacts and downsamples blocks in object storage |
| `thanos-store-shard{0,1,2}` | Serves historical metrics from object storage |
| `thanos-bucket-web` | Web UI for browsing object storage blocks |
| `thanos-ruler` | Evaluates recording and alerting rules against Thanos |
| `memcached` | Caches query results for the query frontend |
