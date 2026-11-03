# RustFS

Deploys a single-node [RustFS](https://rustfs.com) S3-compatible object storage instance (server image `rustfs/rustfs:1.0.3`, bucket-creation client `pgsty/mc:RELEASE.2026-10-18T00-00-00Z`) in the `object-storage` namespace. RustFS provides S3-compatible storage for the Iceberg lakehouse warehouse, Trino fault-tolerance spooling, Thanos long-term metrics storage and Spark event logs. A Job runs after deployment to pre-create the required buckets and to configure the `spark-event-logs` bucket (3-day expiry and a completion notification to Kafka).

## Deployed Resources

```
Namespace: object-storage
├── rustfs                               (Deployment)
└── rustfs-create-bucket                 (Job)

Namespace: kafka
└── spark-event-log-completions          (KafkaTopic, 1 partition, 3 replicas)
```

## Namespaces

- `object-storage`
- `kafka` (only the `spark-event-log-completions` KafkaTopic; the Kafka cluster is wave `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `rustfs` | S3-compatible object storage server (runs as uid 10001; an init container fixes hostPath ownership) |
| `rustfs-create-bucket` | Job that creates the buckets (`mc`, init container) and sets the `spark-event-logs` lifecycle and notification (`aws s3api`, `amazon/aws-cli:2.38.1`). `bootstrap.sh` deletes the completed Job before applying, so every bootstrap re-runs it; every step is idempotent |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `rustfs` | 9000 | S3-compatible API endpoint (`http://rustfs.object-storage.svc.cluster.local:9000`, path-style) |
| `rustfs-console` | 9001 (NodePort 30901) | RustFS web console |

## Memory

The `rustfs` container has a memory request of `1638Mi` and a limit of `3072Mi`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.

The limit was first `2176Mi` (1630 MiB measured before plus about 30%). Under the table maintenance e2e load the container reached that limit and was OOMKilled once; the next e2e run peaked at 2316 MiB, so the limit is that load peak plus about 30%. RustFS 1.0.3 has no documented cache or memory cap setting, so the limit is raised instead.

Measured on the deployed configuration (2026-11-01, after a clean onboard, a table maintenance `e2e.sh` run and a 30 minute soak with no changes, 14:05–14:35): 765 MiB idle before any load, 2316 MiB right after the e2e, 1527 MiB at the end of the soak, no restart. The working set after load stayed above the `832Mi` request, so on 2026-11-03 the request was raised to `1638Mi` (about 1.6Gi); the limit is unchanged.

Measured on 2026-11-03 after a clean onboard, two `e2e.sh` runs and a 30 minute soak (00:44–01:14): peak 1666 MiB, 1628 MiB right after the e2e, 1224 MiB at the end of the soak, no restart.

## Buckets

| Bucket | Used by |
|--------|---------|
| `retail-lakehouse-7dj2` | Iceberg warehouse (Polaris catalog) |
| `trino-fault-tolerance-nkm5`, `trino-fault-tolerance-cws0` | Trino fault-tolerant execution spooling |
| `thanos` | Thanos (on hold) |
| `spark-event-logs` | Spark event logs of the table maintenance jobs |

## Spark event logs bucket

`spark-event-logs` holds the rolling event logs written by the table maintenance Spark jobs (`eventlog_v2_<appId>/events_<N>_<appId>[.zstd]` plus the marker `appstatus_<appId>.inprogress`). The bucket is not versioned.

**Lifecycle.** One rule, `expire-after-3-days`, on the whole bucket (`Filter.Prefix = ""`) expires current objects after 3 days. RustFS answers every PUT with `x-amz-expiration: expiry-date="<day + 3, rounded up to midnight UTC>", rule-id="expire-after-3-days"`, but the deletion itself is done lazily by RustFS's background scanner, so an object can outlive its expiry date for a while.

**Completion notification.** When Spark stops, it renames `appstatus_<appId>.inprogress` to `appstatus_<appId>`; S3A does a rename as CopyObject plus DeleteObject. The bucket has one rule that sends only `s3:ObjectCreated:Copy` events for keys with prefix `eventlog_v2_` to the Kafka target, so a completed application produces exactly one message and event-file PUTs, multipart uploads and deletes produce none. An application that fails hard or is killed never renames its marker and produces no message.

| Setting | Value |
|---------|-------|
| Kafka target (env on the `rustfs` container) | `RUSTFS_NOTIFY_ENABLE=true`, `RUSTFS_NOTIFY_KAFKA_{ENABLE,BROKERS,TOPIC,ACKS,QUEUE_DIR}_SPARK_EVENT_LOGS` |
| Target ID / ARN | `spark_event_logs` / `arn:rustfs:sqs:us-east-1:spark_event_logs:kafka` |
| Brokers | `kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092` (plain listener), `acks=-1` |
| Topic | `spark-event-log-completions` |
| Queue directory | `/notify-queue/spark-event-logs` (hostPath `/home/docker/data/rustfs-notify-queue`) |
| Bucket rule | `s3:ObjectCreated:Copy`, prefix `eventlog_v2_` |

The queue directory is its own hostPath rather than a directory under `/data`, so that queue files stay out of RustFS's storage volume.

**Message format.** The Kafka key is `<bucket>/<URL-encoded object key>`, for example `spark-event-logs/eventlog_v2_test-1%2Fappstatus_test-1`. The value is the S3 event JSON: top-level `EventName` and `Key` (`spark-event-logs/eventlog_v2_test-1/appstatus_test-1`, decoded) and one `Records[]` entry with `eventName` `s3:ObjectCreated:Copy`, `eventTime`, `s3.bucket.name`, `s3.object.key` (URL-encoded, decode it), `size`, `eTag` and `requestParameters.x-amz-copy-source` (the `.inprogress` source key). `awsRegion` is empty and the Kafka record timestamp is `0`; use `eventTime`. Delivery is at least once: consumers must be idempotent on the object key.

**Kafka outages.** The Kafka target connects lazily, so RustFS starts and stays Ready while Kafka is missing or unreachable (on a fresh onboard RustFS starts in the same wave as Kafka, before the brokers are Ready). Each event is first written to the queue directory and then replayed until Kafka accepts it (log line `Kafka not reachable, event remains in store.`, warn level). The queue holds up to 100000 events (RustFS default) and survives RustFS restarts because it is on a hostPath.

**RustFS 1.0.3 findings** (checked against the running image and the `1.0.3` source):
- Target env vars are `RUSTFS_NOTIFY_KAFKA_<KEY>_<TARGET>`; keys are `ENABLE`, `BROKERS` (comma-separated), `TOPIC`, `ACKS` (`0`, `1`, `-1`, `all`), `TLS_*`, `SASL_*`, `QUEUE_DIR` (absolute path), `QUEUE_LIMIT`. The target ID is the lowercase suffix. Targets are read at start-up only, so changing them needs a RustFS restart.
- `s3:ObjectCreated:Copy` is a distinct event (CopyObject emits it; PUT emits `:Put`, multipart emits `:CompleteMultipartUpload`). A rule holds at most one prefix and one suffix filter.
- `mc event add` has no event name for Copy alone (`put` means `s3:ObjectCreated:*`), so the Job uses `aws s3api put-bucket-notification-configuration`. That call replaces the whole configuration, and the lifecycle call (`put-bucket-lifecycle-configuration`) does too, which keeps a re-run idempotent; `mc ilm rule add` would append a duplicate rule on every run.
- `PutBucketNotificationConfiguration` returns success even for an ARN with no configured target; RustFS only logs `ARN not found` (warn) and delivers nothing. `validate.sh` checks the saved configuration, so a renamed target must be renamed in both the env and the rule.
