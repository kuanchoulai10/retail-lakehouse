# Spark Event Logs to RustFS with Completion Events in Kafka — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every table-maintenance Spark job writes a compressed, rolling event log to the RustFS bucket
`spark-event-logs`. The bucket deletes objects after 3 days. When a job's event log completes, RustFS publishes
exactly one object-created event to the Kafka topic `spark-event-log-completions`, where a later runtime will
analyse the metrics.

**Architecture:**
- **Spark side.** The backend's SparkApplication renderer
  (`adapter/outbound/table_maintenance_run/k8s/spark_application_manifest.py`) adds the event log `sparkConf`
  keys and the `hadoop-aws` jars, so that the `s3a://` event log dir works. The S3A settings come from the
  `SparkK8sConfig` the renderer already receives.
- **RustFS side.** The wave-20 RustFS manifests do three things:
  - create the bucket;
  - set a lifecycle expiry of 3 days;
  - configure a Kafka notification target, plus a bucket notification that fires only for the completion
    marker.
- **Kafka side.** The topic is a Strimzi `KafkaTopic`.

**Tech Stack:** Spark 4.0.0 (Hadoop 3.4.x client), hadoop-aws S3A, RustFS 1.0.3 (bucket lifecycle and event
notifications with a Kafka target), pgsty/mc, Strimzi KafkaTopic, Python backend (pytest, ty, ruff, import-linter).

**Spec:** none. The owner gave the requirements in chat and asked for sensible defaults without further
questions. They are recorded verbatim under "Owner requirements" below; the "Decisions" lines are Claude's calls.

## Owner requirements (verbatim intent)

- Spark event logs go to the RustFS bucket `spark-event-logs`, compressed.
- The bucket has a lifecycle rule that deletes files after 3 days.
- RustFS sends an S3-style object-created event for the completion marker only: the moment
  `appstatus_<appId>.inprogress` becomes `appstatus_<appId>`.
- Events go to Kafka. A future runtime will consume them and analyse the metrics.
- Spark conf includes `spark.eventLog.logStageExecutorMetrics=true`, `spark.eventLog.rolling.enabled=true` and
  `spark.eventLog.rolling.maxFileSize=128m`.

## Decisions (Claude's calls)

- **Spark conf, added to every maintenance SparkApplication:**
  - `spark.eventLog.enabled=true`
  - `spark.eventLog.dir=s3a://spark-event-logs/`
  - `spark.eventLog.compress=true`
  - `spark.eventLog.compression.codec=zstd`
  - the owner's three keys above

  The bucket name and dir are configurable through `SparkK8sConfig` (default `s3a://spark-event-logs/`). The
  composition root wires it from settings in the same way as the existing `s3_endpoint`.
- **S3A:**
  - `spark.hadoop.fs.s3a.endpoint` = the same endpoint as the Iceberg `s3.endpoint`.
  - `spark.hadoop.fs.s3a.path.style.access=true`
  - `spark.hadoop.fs.s3a.connection.ssl.enabled=false` when the endpoint is `http://`.
  - Credentials come from the same Secret env the driver and executor already get (`envFrom` the S3 secret),
    through `EnvironmentVariableCredentialsProvider`. Check the key names; map them in `sparkConf` or the env if
    they are not `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.
- **Jars:** `org.apache.hadoop:hadoop-aws` at the exact Hadoop version bundled in `apache/spark:4.0.0`, plus the
  AWS SDK v2 jar it needs. Add them to `deps.jars` (Maven Central URLs, like the Iceberg jars).
  - If `iceberg-aws-bundle` already provides the SDK v2 classes S3A needs, add only `hadoop-aws`, and prove that
    with a real run.
  - Baking jars into the image stays an existing follow-up; do not do it here.
- **Completion-only events:**
  - Spark's rolling writer creates `eventlog_v2_<appId>/appstatus_<appId>.inprogress` at start, and at stop
    renames it to `appstatus_<appId>`.
  - S3A renames by CopyObject plus DeleteObject. The event files are written with PUT or multipart.
  - So the bucket notification subscribes only to `s3:ObjectCreated:Copy`, with prefix `eventlog_v2_`.
  - Fallback, if RustFS does not emit a distinct Copy event type (verify in Task 1): subscribe to all
    `s3:ObjectCreated:*` events with prefix `eventlog_v2_`. Document that the consumer must keep only keys whose
    basename starts with `appstatus_` and does not end in `.inprogress`, and record why.
- **Kafka topic:** `spark-event-log-completions` in namespace `kafka`, with 1 partition and 3 replicas (like
  `polaris-catalog-events`). The RustFS Kafka target points at the plain listener
  `kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092`. Its queue directory lives on RustFS's data
  volume, so events survive a Kafka outage.
- **Lifecycle:** one rule on the whole bucket expiring current objects after 3 days. The bucket is not
  versioned. Note in the README that RustFS's background scanner applies expiry lazily.

## Global Constraints

- Owner values, exactly:
  - bucket `spark-event-logs`
  - expiry 3 days
  - `spark.eventLog.logStageExecutorMetrics=true`
  - `spark.eventLog.rolling.enabled=true`
  - `spark.eventLog.rolling.maxFileSize=128m`
  - compression on
- Topic name `spark-event-log-completions`. Events must be completion-only, or the documented fallback above.
- Backend rules (CLAUDE.md):
  - TDD.
  - Every commit passes `pytest -v`, `ty check`, `ruff check .`, `lint-imports` and `task pre-pr`.
  - One object per file, `from __future__ import annotations`.
  - No infrastructure terms in `application/`. These changes live in the k8s adapter and bootstrap.
- Infra rules:
  - No explanatory comments in YAML.
  - kubectl verb first, flags last. A redirect after kubectl flags is rejected.
  - `kubectl label/annotate/patch/scale/replace` and `rm -rf` are hook-blocked.
  - Pass `KUBE_CONTEXT=retail-lakehouse`.
  - Never print secret values.
- Git:
  - Commit on `main`, never push.
  - Never stage `docs/architecture.excalidraw.svg`.
  - Conventional commits, lines ≤ 100 chars, ending with a blank line and
    `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- Memory: the node has about 6.6 GiB of request headroom for Spark. Do not raise Spark driver or executor memory.

## Review Focus

1. **A job that fails or is killed** never renames its `.inprogress` marker, so no completion event is sent. That
   is acceptable, but document it for the consumer. Pinned by Task 3, Step 2 (README note).
2. **RustFS starting before Kafka is ready** on a fresh onboard. The target must queue to disk and not crash-loop
   RustFS. Pinned by Task 1, Step 5: RustFS is Ready while the topic does not exist yet, and the event is
   delivered later.
3. **S3A misconfigured.** For example, missing credentials or SSL attempted on an `http` endpoint. The driver
   would fail at start-up, which breaks every maintenance run. Pinned by Task 2, Step 6: `e2e.sh` passes and every
   run succeeds.
4. **Duplicate events per job.** Pinned by Task 2, Step 7: exactly one message per Spark application.
5. **Big event logs roll at 128m** and produce several `events_N_` files. They must not trigger events. Pinned by
   Task 1, Step 4: put plus multipart produce no message.

---

### Task 1: RustFS bucket, lifecycle, Kafka target, completion notification and topic

**Files:**
- Modify: `platform/20-rustfs/rustfs.yaml`. The bucket Job adds `spark-event-logs` to its list, applies the
  lifecycle rule, and sets the bucket notification. The RustFS Deployment gets the Kafka target env.
- Create: `platform/20-rustfs/spark-event-log-completions-topic.yaml` (`KafkaTopic`, namespace `kafka`, label
  `strimzi.io/cluster: kafka-cluster`, 1 partition, 3 replicas). Apply it from `20-rustfs/bootstrap.sh` and check
  it is `Ready` in `validate.sh`. Wave 20 applies `20-kafka-cluster` first; check the order in `tasks/apps.yml`.
- Modify: `platform/20-rustfs/validate.sh`. Check:
  - the bucket exists;
  - the lifecycle rule lists a 3-day expiry;
  - the notification config names the Kafka target ARN.
- Modify: `platform/20-rustfs/README.md`.

**Interfaces:** produces the bucket `spark-event-logs`, the topic `spark-event-log-completions`, and the event
contract (the S3 event JSON from RustFS). Task 2 writes to the bucket and reads the topic.

- [ ] **Step 1: Confirm RustFS 1.0.3 capabilities against the running image.** Find:
  - the Kafka target env names (`RUSTFS_NOTIFY_KAFKA_*_<TARGET>`) from docs.rustfs.com "Event Notifications"
    and the `rustfs-targets` crate;
  - how to put a lifecycle rule (`mc ilm rule add --expire-days 3`, or the S3 `PutBucketLifecycleConfiguration`
    API);
  - whether a notification rule can name `s3:ObjectCreated:Copy`. Use `mc event add` with the needed event list,
    or `PutBucketNotificationConfiguration` through an S3 client available in a throwaway pod, such as
    `amazon/aws-cli` pinned by version.

  Record the findings in the README.
- [ ] **Step 2: Write the failing checks.** Add the new `validate.sh` assertions and run them. Expected: they FAIL
  (bucket missing).
- [ ] **Step 3: Implement and apply.** Run `KUBE_CONTEXT=retail-lakehouse bash platform/20-rustfs/bootstrap.sh`.
  The Deployment env change restarts RustFS, and the Job re-runs. Delete the completed Job first, because Job
  specs are immutable; follow whatever the bootstrap already does. Then run validate. Expected: PASS.
- [ ] **Step 4: Prove completion-only delivery with a synthetic run.**
  1. Start a consumer on `spark-event-log-completions` with `kafka-console-consumer.sh` in a broker pod.
  2. From a throwaway pod, put `eventlog_v2_test-1/appstatus_test-1.inprogress` (empty) and
     `eventlog_v2_test-1/events_1_test-1.zstd`, plus one file above 16 MiB so it uploads as multipart.
  3. Server-side copy `appstatus_test-1.inprogress` to `appstatus_test-1`, then delete the source. This is what
     S3A rename does.

  Expected: exactly one message, for key `eventlog_v2_test-1/appstatus_test-1`, with `eventName`
  `s3:ObjectCreated:Copy`. If RustFS cannot tell Copy apart from Put, switch to the documented fallback, prove
  which messages arrive, and record that. Then delete the test objects.
- [ ] **Step 5: Kafka-down tolerance.** Check that RustFS's Kafka target queues to disk, by reading its logs
  while the topic exists. Document the behaviour on a fresh onboard (RustFS in wave 20 may start before Kafka is
  Ready). RustFS must stay Ready either way. Do not take Kafka down on purpose.
- [ ] **Step 6: Commit.** `feat(platform): spark-event-logs bucket with 3-day expiry and completion events`.

### Task 2: Spark event logs from every maintenance job

**Files:**
- Modify: `src/table-maintenance/backend/adapter/outbound/table_maintenance_run/k8s/spark_k8s_config.py`: add
  `event_log_dir: str = "s3a://spark-event-logs/"`, plus any S3A fields needed.
- Modify: `…/k8s/spark_application_manifest.py`: event log keys, S3A keys, and the hadoop-aws jar(s) in `_jars`.
- Modify: the bootstrap container and settings wiring, only if a new setting must come from `GLAC_` env. The
  default must be correct with no env.
- Test: `src/table-maintenance/backend/tests/adapter/outbound/table_maintenance_run/k8s/test_spark_k8s_gateways.py`
  (or a new `test_spark_application_manifest.py` beside it, following the existing test layout).

**Interfaces:** consumes Task 1's bucket. Produces SparkApplications whose `sparkConf` contains exactly:

```
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://spark-event-logs/
spark.eventLog.compress=true
spark.eventLog.compression.codec=zstd
spark.eventLog.logStageExecutorMetrics=true
spark.eventLog.rolling.enabled=true
spark.eventLog.rolling.maxFileSize=128m
spark.hadoop.fs.s3a.endpoint=<config.s3_endpoint>
spark.hadoop.fs.s3a.path.style.access=true
```

The SSL, credentials-provider and any other S3A keys come from Step 4's findings.

- [ ] **Step 1: Write the failing test** `test_spark_application_enables_compressed_rolling_event_log`. Render a
  SparkApplication with a test `SparkK8sConfig`, then assert each key and value above in `spec.sparkConf`, and
  that `spec.deps.jars` contains a `hadoop-aws` jar URL with the pinned version.
- [ ] **Step 2: Run it.** Command: `uv run --project src/table-maintenance/backend --directory
  src/table-maintenance/backend pytest tests/adapter/outbound/table_maintenance_run/k8s -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Find the Hadoop version with `ls /opt/spark/jars | grep hadoop-client` in an
  `apache/spark:4.0.0` container or the `table-maintenance-spark` image. Pin `hadoop-aws` to it.
- [ ] **Step 4: Run the full backend checks.** `pytest -v`, `ty check`, `ruff check .`, `lint-imports`. Expected:
  all pass, including the architecture tests.
- [ ] **Step 5: Build and deploy.** Run `platform/25-lakehouse-control-plane/build.sh`, then
  `bootstrap.sh` and `validate.sh` with `KUBE_CONTEXT=retail-lakehouse`, as in the wave README.
- [ ] **Step 6: Run `e2e.sh` end to end.** Expected: PASS, with all four procedures SUCCEEDED. The bucket now holds
  one `eventlog_v2_<appId>/` per SparkApplication, each with a `.zstd` events file and an `appstatus_<appId>` with
  no `.inprogress` left.
- [ ] **Step 7: Kafka contract.** The topic holds exactly one message per Spark application run during the e2e.
  Count the distinct `eventlog_v2_*` dirs and the messages, and compare. Save one sample message (redact nothing
  secret; there should be none) to the wave-25 README as the event contract example.
- [ ] **Step 8: Commit.**
  `feat(table-maintenance): write compressed rolling Spark event logs to RustFS`.

### Task 3: Docs

**Files:** `CLAUDE.md`, `platform/20-rustfs/README.md`, `platform/25-lakehouse-control-plane/README.md`.

- [ ] **Step 1: CLAUDE.md.**
  - Data flow line: add "Spark maintenance event logs → RustFS `spark-event-logs` (zstd, rolling 128m, 3-day
    expiry) → completion events → Kafka `spark-event-log-completions`".
  - Add a 2026-11-04 history line.
  - Add follow-ups:
    - a consumer runtime does not exist yet;
    - a failed or killed job sends no completion event;
    - whichever event filter was chosen (Copy-only or the fallback), with the reason.
- [ ] **Step 2: READMEs.** Cover:
  - the event contract with the sample message;
  - the key layout `eventlog_v2_<appId>/{events_N_<appId>.zstd, appstatus_<appId>}`;
  - that expiry is lazy (background scanner);
  - the failed-job note.
- [ ] **Step 3: Run `task pre-pr`, then commit.**
  `docs(platform): document Spark event logs and completion events`.
