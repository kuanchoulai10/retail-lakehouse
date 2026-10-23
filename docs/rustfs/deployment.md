# RustFS Deployment

RustFS (`rustfs/rustfs`, pinned to `1.0.3`) is the S3-compatible object store in the `object-storage` namespace. It serves the Iceberg warehouse, Trino fault-tolerance spooling, and Thanos long-term storage. It replaced the previous MinIO (Silo) deployment.

```bash
bash platform/20-rustfs/bootstrap.sh
bash platform/20-rustfs/validate.sh
```

| Item | Value |
|------|-------|
| S3 endpoint (path-style) | `http://rustfs.object-storage.svc.cluster.local:9000` |
| Console | Service `rustfs-console`, NodePort 30901 |
| Credentials | Secret `rustfs-secret` (`RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY`) |
| Data directory | hostPath `/home/docker/data/rustfs` (container uid 10001; an init container chowns it) |
| Health endpoint | `GET /health` on port 9000 |

A Job named `rustfs-create-bucket` pre-creates the `retail-lakehouse-7dj2`, `trino-fault-tolerance-nkm5`, `trino-fault-tolerance-cws0` and `thanos` buckets.
