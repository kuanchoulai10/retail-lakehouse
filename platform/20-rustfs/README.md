# RustFS

Deploys a single-node [RustFS](https://rustfs.com) S3-compatible object storage instance (server image `rustfs/rustfs:1.0.3`, bucket-creation client `pgsty/mc:RELEASE.2026-10-18T00-00-00Z`) in the `object-storage` namespace. RustFS provides S3-compatible storage for the Iceberg lakehouse warehouse, Trino fault-tolerance spooling, and Thanos long-term metrics storage. A Job runs after deployment to pre-create the required buckets.

## Deployed Resources

```
Namespace: object-storage
├── rustfs                               (Deployment)
└── rustfs-create-bucket                 (Job)
```

## Namespaces

- `object-storage`

## Pods

| Pod | Purpose |
|-----|---------|
| `rustfs` | S3-compatible object storage server (runs as uid 10001; an init container fixes hostPath ownership) |
| `rustfs-create-bucket` | One-time job that creates the required buckets on startup |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `rustfs` | 9000 | S3-compatible API endpoint (`http://rustfs.object-storage.svc.cluster.local:9000`, path-style) |
| `rustfs-console` | 9001 (NodePort 30901) | RustFS web console |

## Memory

The `rustfs` container has a memory limit of `2176Mi` (the 1630 MiB measured before the change plus about 30% headroom) and a request of `832Mi`, just above the 765 MiB it used after a 30 minute soak. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled. Under the table maintenance e2e load (2026-11-01) the container grew from 765 MiB to the 2176Mi limit and was OOMKilled once, so the limit is too low for maintenance load and should be raised from a load measurement. Right after the restart it used about 300 MiB, so the figure reflects a long-running pod; lower the limit if later measurements stay well under it.
