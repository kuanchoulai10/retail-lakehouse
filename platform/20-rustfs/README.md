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
