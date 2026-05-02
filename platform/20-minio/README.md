# MinIO

Deploys a single-node MinIO object storage instance in the `minio` namespace. MinIO provides S3-compatible storage for the Iceberg lakehouse warehouse, Trino fault-tolerance spooling, and Thanos long-term metrics storage. A Job runs after deployment to pre-create the required buckets.

## Deployed Resources

```
Namespace: minio
├── minio                                (Deployment)
└── minio-create-bucket                  (Job)
```

## Namespaces

- `minio`

## Pods

| Pod | Purpose |
|-----|---------|
| `minio` | S3-compatible object storage server |
| `minio-create-bucket` | One-time job that creates the required buckets on startup |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `minio-api` | 9000 | S3-compatible API endpoint |
| `minio-console` | 9001 (NodePort 30901) | MinIO web console |
