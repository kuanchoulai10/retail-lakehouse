# Apache Polaris

Deploys Apache Polaris (incubating) as the Iceberg REST catalog layer into the `polaris` namespace. Polaris manages Iceberg catalog metadata (namespaces, tables, schemas) while data files reside in MinIO.

## Deployed Resources

```
Namespace: polaris
├── polaris                              (Deployment)
├── polaris                              (Service, port 8181)
└── polaris-management                   (Service headless, port 8182)
```

## Namespaces

- `polaris`

## Pods

| Pod | Purpose |
|-----|---------|
| `polaris` | Iceberg REST catalog server; handles catalog API requests from Trino and Kafka Iceberg connector |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `polaris.polaris.svc.cluster.local` | 8181 | Iceberg REST catalog API |
| `polaris-management` | 8182 | Health checks and Prometheus metrics (headless) |

## Sync Wave

Wave 21 — depends on MinIO (wave 20). Deploys in parallel with the Debezium CDC connector. The Iceberg Kafka connector (wave 22) and Trino (wave 23) depend on Polaris being ready.

## Prerequisites

Before installing, create the storage credentials secret so Polaris can vend credentials to clients (Trino, Iceberg connector) for direct S3 access to MinIO:

```bash
kubectl create namespace polaris --context mini
kubectl create secret generic polaris-storage-secret \
  --from-literal=awsAccessKeyId=<MINIO_ACCESS_KEY> \
  --from-literal=awsSecretAccessKey=<MINIO_SECRET_KEY> \
  -n polaris --context mini
```

## Configuration Notes

The following fields in `values.yaml` require attention before deploying:

| Field | Description | Current Value |
|-------|-------------|---------------|
| `persistence.type` | `in-memory` loses catalog state on pod restart; switch to `relational-jdbc` with PostgreSQL for durability | `in-memory` |
| `storage.secret.name` | K8s Secret with MinIO credentials for vended credential issuance | `polaris-storage-secret` |
| `advancedConfig.polaris.storage.s3.endpoint` | MinIO service DNS inside the cluster | `http://minio.minio.svc.cluster.local:9000` |
| `authentication.tokenBroker.secret.name` | RSA key pair secret; leave blank to auto-generate (keys rotate on restart) | blank |
| `tracing.endpoint` | OTel collector gRPC endpoint | `http://otel-collector.otel.svc.cluster.local:4317` |

## Installation

```bash
bash 21-polaris/install.sh
```

## Uninstallation

```bash
bash 21-polaris/uninstall.sh
```

## Validation

```bash
bash 21-polaris/validate.sh
```

## Post-Install Bootstrap

After Polaris is running, create the initial catalog pointing to MinIO:

```bash
# Get the root credentials from the Polaris pod logs on first start
kubectl logs -l app.kubernetes.io/name=polaris -n polaris --context mini | grep -i "root credentials"

# Use the Polaris admin CLI or REST API to create a catalog:
# POST /api/management/v1/catalogs
# {
#   "name": "iceberg",
#   "type": "INTERNAL",
#   "properties": {
#     "default-base-location": "s3://retail-lakehouse-<ID>/warehouse"
#   },
#   "storageConfigInfo": {
#     "storageType": "S3",
#     "allowedLocations": ["s3://retail-lakehouse-<ID>/"],
#     "roleArn": ""
#   }
# }
```
