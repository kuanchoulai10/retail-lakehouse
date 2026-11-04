# Apache Polaris

Deploys Apache Polaris (incubating) as the Iceberg REST catalog layer into the `lakehouse-catalog` namespace. Polaris manages Iceberg catalog metadata (namespaces, tables, schemas) while data files reside in RustFS.

## Deployed Resources

```
Namespace: lakehouse-catalog
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
| `polaris.lakehouse-catalog.svc.cluster.local` | 8181 | Iceberg REST catalog API |
| `polaris-management` | 8182 | Health checks and Prometheus metrics (headless) |

## Sync Wave

Wave 21 — depends on RustFS (wave 20, S3 storage) and polaris-db (wave 20, catalog persistence). The Iceberg Kafka connector (wave 22) and Trino (wave 23) depend on Polaris being ready.

## Prerequisites

Before installing, create the storage credentials secret so Polaris can vend credentials to clients (Trino, Iceberg connector) for direct S3 access to RustFS:

```bash
kubectl apply -f - --context retail-lakehouse <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: lakehouse-catalog
  labels:
    istio.io/dataplane-mode: ambient
EOF
kubectl create secret generic polaris-storage-secret \
  --from-literal=awsAccessKeyId=<RUSTFS_ACCESS_KEY> \
  --from-literal=awsSecretAccessKey=<RUSTFS_SECRET_KEY> \
  -n lakehouse-catalog --context retail-lakehouse
```

## Configuration Notes

The following fields in `values.yaml` require attention before deploying:

| Field | Description | Current Value |
|-------|-------------|---------------|
| `persistence.type` | Backed by PostgreSQL deployed in wave 20 by [`20-polaris-db/`](../20-polaris-db/README.md). Catalog state is durable across pod restarts. | `relational-jdbc` |
| `storage.secret.name` | K8s Secret with RustFS credentials for vended credential issuance | `polaris-storage-secret` |
| `advancedConfig.polaris.storage.s3.endpoint` | RustFS service DNS inside the cluster | `http://rustfs.object-storage.svc.cluster.local:9000` |
| `authentication.tokenBroker.secret.name` | RSA key pair secret `polaris-token-broker` (`private.pem` / `public.pem`), created once by `bootstrap.sh` if missing, so tokens issued to Trino and the Iceberg sink survive Polaris restarts | `polaris-token-broker` |
| `advancedConfig.polaris.event-listener.types` | Publishes every Polaris catalog event to Kafka (the OpenTelemetry listener cannot be used: the image fixes `quarkus.otel.logs.enabled=false` at build time) | `kafka` |
| `advancedConfig.polaris.event-listener.kafka.topic` | Topic declared as a `KafkaTopic` by `polaris-events-topic.yaml` (1 partition, 3 replicas, so the UUID-keyed events stay ordered) | `polaris-catalog-events` |
| `advancedConfig.polaris.event-listener.kafka.properties.bootstrap.servers` | Strimzi plain listener | `kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092` |
| `tracing.enabled` | OTel tracing is off | `false` |

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

After Polaris is running, create the initial catalog pointing to RustFS:

```bash
# Get the root credentials from the Polaris pod logs on first start
kubectl logs -l app.kubernetes.io/name=polaris -n lakehouse-catalog --context retail-lakehouse | grep -i "root credentials"

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

### Smoke Test: Catalog Persistence

Verify that catalog state survives a Polaris pod restart (impossible under the old `in-memory` mode):

```bash
# 1. Get the root credentials from the first-start logs
kubectl logs -l app.kubernetes.io/name=polaris -n lakehouse-catalog --context retail-lakehouse \
  | grep -i "root credentials"

# 2. Use the Polaris admin REST API (via kubectl exec) to create a catalog.
#    See the example POST body above in this section.

# 3. Restart Polaris
kubectl rollout restart deployment/polaris -n lakehouse-catalog --context retail-lakehouse
kubectl rollout status deployment/polaris -n lakehouse-catalog --context retail-lakehouse

# 4. List catalogs again — the test catalog must still be present.
#    Use the same admin REST API endpoint.

# 5. Verify the metadata tables exist in PostgreSQL
POD=$(kubectl get pod -l app.kubernetes.io/name=postgres,app.kubernetes.io/instance=polaris-db -n lakehouse-catalog --context retail-lakehouse \
  -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n lakehouse-catalog "$POD" --context retail-lakehouse \
  -- psql -U polaris -d polaris -c '\dt'
```

## Event Listener

Polaris publishes catalog events (key: event UUID, value: JSON with `event_type`, `catalog_name`, `namespace`, `table_name`, `principal`, `request_id`, ...) to the `polaris-catalog-events` topic. Read them with:

```bash
kubectl exec kafka-cluster-dual-role-0 --namespace kafka --context retail-lakehouse -- bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic polaris-catalog-events --from-beginning
```
