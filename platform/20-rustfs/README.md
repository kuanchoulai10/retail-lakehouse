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

The `rustfs` container has a memory request of `832Mi` and a limit of `3072Mi`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.

The limit was first `2176Mi` (1630 MiB measured before plus about 30%). Under the table maintenance e2e load the container reached that limit and was OOMKilled once; the next e2e run peaked at 2316 MiB, so the limit is that load peak plus about 30%. RustFS 1.0.3 has no documented cache or memory cap setting, so the limit is raised instead.

Measured on the deployed configuration (2026-11-01, after a clean onboard, a table maintenance `e2e.sh` run and a 30 minute soak with no changes, 14:05–14:35): 765 MiB idle before any load, 2316 MiB right after the e2e, 1527 MiB at the end of the soak, no restart. The working set after load stays above the request; raise the request to about 1.6Gi if scheduling headroom allows.
