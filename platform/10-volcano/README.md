# Volcano

Deploys the Volcano batch scheduler via Helm. Volcano queues batch workloads and schedules each one's pods as a group (gang scheduling), so a job starts only when all of its pods fit. The Spark Operator (wave 11) hands Spark applications to it when a `SparkApplication` sets `spec.batchScheduler: volcano`; the operator then creates a `PodGroup` for the driver and executors and their pods use the `volcano` scheduler. Pods that do not ask for Volcano keep the default Kubernetes scheduler.

Volcano installs before the Spark Operator because the operator's Volcano integration needs the `PodGroup` CRD to exist.

## Deployed Resources

```
Namespace: volcano-system
├── volcano-admission                (Deployment)
├── volcano-admission-init           (Job)
├── volcano-controllers              (Deployment)
└── volcano-scheduler                (Deployment)
```

## Namespaces

- `volcano-system` (an operator namespace, not enrolled in the ambient mesh)

## Pods

| Pod | Purpose |
|-----|---------|
| `volcano-admission` | Admission webhooks that validate and default Volcano jobs, pod groups and queues |
| `volcano-admission-init` | One-off Job that creates the webhook certificate Secret |
| `volcano-controllers` | Reconciles Volcano jobs, pod groups and queues; creates the `default` queue |
| `volcano-scheduler` | Schedules pods whose `schedulerName` is `volcano` |

## Scheduler configuration

The chart's default: actions `enqueue, allocate, backfill` (no `preempt` or `reclaim`, so a running job is never evicted), plugins `priority`, `gang`, `conformance`, `overcommit`, `drf`, `predicates`, `proportion`, `nodeorder`, `binpack`. Every pod group without a queue lands in the `default` queue.

## CRDs

| CRD | Purpose |
|-----|---------|
| `queues.scheduling.volcano.sh` | A queue that pod groups wait in, with a weight and an optional capacity |
| `podgroups.scheduling.volcano.sh` | A group of pods scheduled together (gang), with a minimum member count and resources |
| `jobs.batch.volcano.sh` | Volcano's own batch job (not used here) |
| `commands.bus.volcano.sh` | Commands sent to Volcano jobs (abort, restart) |
| `cronjobs.batch.volcano.sh` | Cron-scheduled Volcano jobs (not used here) |
| `jobflows.flow.volcano.sh`, `jobtemplates.flow.volcano.sh` | Job dependency flows (not used here) |
| `hypernodes.topology.volcano.sh` | Network topology for topology-aware scheduling (not used here) |
| `namespacequeues.scheduling.volcano.sh` | Binds a namespace to a queue (not used here) |
| `numatopologies.nodeinfo.volcano.sh` | Node NUMA topology (not used here) |
| `nodeshards.shard.volcano.sh` | Splits nodes across scheduler shards (not used here) |
| `colocationconfigurations.config.volcano.sh` | Online and offline workload colocation (not used here) |
