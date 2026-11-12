# Tables keep themselves healthy: roadmap milestones 1-5

Status: approved for planning, 2026-11-13. Covers how the five milestones of the Linear project P-KCL-6 「表自己保持健康，不用人盯」 (issues KCL-46..63) are built, verified and reported. The project description in Linear holds the goal, the references and the end-state picture; this document holds the decisions that make it buildable.

## Why

**Table maintenance works for small tables run one at a time, and breaks in the ways that matter at scale.** A timed-out attempt is retried while its Spark job may still run, so the same work can be submitted twice and the admission limit (2) is not real. Every attempt uses the same Spark size, so an out-of-memory failure is retried three times into the same wall. Reconcile looks at whole tables, so a table with millions of partitions cannot be observed cheaply, and nothing ranks which work is worth the compute. The goal: the platform picks maintenance worth doing, runs it with just enough resources, recovers from failures by itself, never submits the same work twice, and copes with very large tables.

## Goals

- Milestone 1, fix the timeout gap (KCL-46, 47): a timed-out attempt deletes its SparkApplication and waits for its pods to be gone before the admission slot is released and before the next attempt is submitted.
- Milestone 2, failure classes and OOM escalation (KCL-48..52): Spark sizes S / M / L; every failed attempt is classified; on out-of-memory the next attempt uses the next size and less work; each table remembers its last successful size; the console shows the size and failure reason of every attempt.
- Milestone 3, partition candidates and benefit / cost (KCL-53..57): a partition candidate table, filtered and scored; one run compacts only the top N partitions; the console shows each partition's benefit, cost and score; incremental observation as described below.
- Milestone 4, priorities and budget scheduling (KCL-58..60): P0 / P1 / P2 on the maintenance policy; one global scheduler picks, per round, by score × priority within a GB·hour budget; the console shows what each round picked and why.
- Milestone 5, Spark pools that pull work (KCL-61..63), in the reduced form below.
- A final summary of all five milestones, written as a comment on the Linear project.

## Non-goals

- Final S / M / L numbers. They only need to make OOM reproducible and an S → M escalation observable.
- Automatic parsing of Spark event log contents. This round records whether the event log finished cleanly; parsing comes later.
- Pools that stay warm. Minikube has 8 CPUs and 26 GB; idle pools must cost nothing.
- Multi-tenancy, external principals, anything outside the table maintenance context.

## Anti-goals

- **Never two maintenance operations on one table at the same time.** The per-table reconciliation workflow stays the only dispatcher (ADR 0002).
- **Never resubmit while the previous Spark job can still write.** Delete first, confirm the pods are gone, then release and retry.
- **Never trust a Spark report as the last word.** See "Correctness" below.
- **Never full-scan a huge table on every reconcile** once incremental observation exists; until then the full scan is a known, written risk.
- **Never mark a milestone done that was not verified,** or whose unverifiable part is not written down as a risk.

## Correctness: the table decides, the Spark report is a fast path

Spark reports its result by calling the API. That report is used at once: it updates the run and the candidates, feeds the console and calibrates cost. It is not the final word, because it can be wrong in ways the platform has already met:

1. The report is lost (the e2e already handles `completed_without_callback`).
2. The job committed but was killed or timed out before reporting, so a success looks like a failure (the gap milestone 1 fixes).
3. Partial progress commits some file groups and fails others, and the report carries one total.
4. Writers add small files again right after a compaction.

Reconcile already reads table metadata every time it runs, to decide what is due; this rule adds no observation. It only says that when the report and the table disagree, the table wins: a partition the next observation still finds unhealthy becomes a candidate again, whatever Spark said.

## Milestone decisions

### 1. Timeout gap

- On attempt timeout: delete the SparkApplication (the delete-job gateway already exists), poll until no pod with the run / operation / attempt labels remains, then release the admission slot, then back off and retry. Failure to confirm deletion within a bound is a failure of the attempt that keeps the slot held and is surfaced, not silently released.
- The attempt deadline (today 6 h, `DEFAULT_ATTEMPT_DEADLINE_SECONDS`) becomes configurable so verification can set it to about 10 minutes and make a job time out for real (for example a job that sleeps). Production default stays 6 h.
- The admission lease today expires 15 minutes after the attempt deadline and frees the slot by itself. While a timed-out attempt's deletion is unconfirmed, the lease is extended, so the slot stays held until the pods are gone (main session's call).

### 2. Failure classes and OOM

- Sizes S / M / L: arbitrary values, chosen so a crafted job overflows S and fits M. Driver and executor stay capped at 1 core (`coreLimit`, landed 2026-11-12).
- Failure classes at least: `oom`, `timeout`, `commit_conflict`, `other`. OOM is detected from (a) the Kubernetes container status `OOMKilled` / exit code 137 of the driver or executor, and (b) `java.lang.OutOfMemoryError` in the driver's termination message or SparkApplication error. Also record whether the attempt's Spark event log finished (an OOM-killed driver leaves `appstatus_<appId>.inprogress` and RustFS never sends the completion event); this is recorded, not yet parsed.
- On `oom`: next attempt uses the next size (S → M → L; beyond L, stop and hand to a human) and less work per attempt (fewer partitions once milestone 3 exists). `commit_conflict`: same size. `timeout` and `other`: same size, existing attempt limit.
- Escalation uses the existing 3 attempts (S, M, L is exactly three). An OOM at L marks that table's operation **needs attention**: reconcile stops planning that operation for that table, the console says so, and a manual run or a change to the table's applicable policy clears it (main session's call).
- Each table remembers the size of its last successful run and starts there; a run whose measured use is well below the size steps down one size. Measured use comes from what is cheaply available now (pod status / metrics if present); if it cannot be measured on this cluster, step-down is written as a risk.
- Verification: a table and job crafted to overflow S, observe S fail as `oom`, M succeed, and the console show both attempts with size and reason.

### 3. Candidates and scoring

- Candidate table keyed by (table, partition); repeated reconciles update one row; states pending → claimed → running → done / failed with a lease; partitions too small or still being written (recent commit) are filtered out; a partition observed healthy after its run leaves the candidates.
- Score = 0.7 × benefit + 0.3 × cost term, both normalised to [0, 1]; benefit = small files removable; cost = estimated GB·hours (memory × bytes ÷ throughput, throughput from run history with a fixed default until history exists). Higher cost lowers the score.
- One run compacts only the top N partitions of the table (N configurable).
- Candidates sit under the existing policy, they do not replace it (main session's call). The policy's compaction trigger conditions (for example `reducible_files`) stay the gate: a partition becomes a candidate only if it meets them, and the small / recent filters apply on top. A table whose policy compacts the whole table, or an unpartitioned table, has one candidate that stands for the whole table. The policy editor's meaning does not change.
- Scores use fixed reference bounds, not normalisation within one table, so a score means the same on every table and milestone 4 can rank across tables. The score is computed at observation and stored on the candidate (main session's call).
- **Observation is built full-scan first.** The first version reads all partitions every reconcile; our tables are small, so this is cheap and lets candidates, scores and top-N be verified end to end. Incremental observation follows within a bounded effort: remember the last processed snapshot id, read only snapshots after it, take the partitions of ADDED manifest entries (PyIceberg exposes snapshots, manifests and entries), fall back to one full scan when the remembered snapshot has expired. If the edge cases (expired snapshots, compaction's own snapshots, delete files) do not come out clean, ship the full scan and write "large tables are slow to observe" as a risk.

### 4. Priorities and budget

- **The scheduler governs compaction only** (decided 2026-11-13). Reconcile still finds and scores candidates, but starts `rewrite_data_files` only for partitions the scheduler picked; candidates not picked stay pending for the next round. `expire_snapshots`, `rewrite_manifests` and `remove_orphan_files` keep running on the reconcile's own trigger conditions and use no budget. One operation per table at a time still holds between scheduler-picked compaction and timer-driven operations on the same table.
- `priority` P0 / P1 / P2 on the maintenance policy (inheritable like the rest of the policy), default P2.
- One global scheduler workflow per round: rank candidates by score × priority weight, take them in order until the round's GB·hour budget is used, then tell each table's reconciliation workflow which partitions to run. The per-table workflow still dispatches, so one-operation-per-table holds.
- Budget unit GB·hours; defaults small enough that on minikube a round visibly leaves candidates unpicked.
- The console shows each round: what was picked, what was skipped, and why.

### 5. Spark pools, reduced for minikube

- One Temporal task queue per size (S / M / L). A pool is a Deployment whose single pod runs Spark in local mode (driver only, no executors) with a Temporal worker that takes the next task from its own queue.
- KEDA scales each pool from 0 to 1 on queue backlog and back to 0 after an idle period, so idle pools cost nothing. Max 1 pod per pool on this cluster.
- A lost heartbeat marks the task failed; the failure is classified as in milestone 2 (an OOM-killed pod is `oom`) and the next attempt goes to the next size's queue.
- Fencing (main session's call): a lost heartbeat does not prove the pod is dead, so before the retry is sent the platform deletes that pool pod and waits until it is gone, the pool equivalent of milestone 1. The admission limit of 2 still applies across all pools. A pool worker reports its result through the existing callback API, same as a SparkApplication, so the result path does not fork.
- The per-SparkApplication path stays available until the pool path is verified; which path a run uses is a setting.

## Finding a table's workflows in the Temporal UI

**Today you cannot ask Temporal "what is running for this table".** No workflow carries a search attribute, and the maintenance workflow ID holds the table name as of the run start, which a rename breaks. From milestone 1 on, every workflow that acts on one table (reconciliation, maintenance, and later scheduler hand-offs and pool tasks) carries custom search attributes, registered in the Temporal namespace `default` by the Temporal wave's bootstrap:

| Search attribute | Type | Value |
|---|---|---|
| `TableUuid` | Keyword | the table's uuid |
| `TableName` | Keyword | `catalog.namespace.table` at start |
| `MaintenanceOperations` | KeywordList | operations a maintenance run plans |
| `MaintenanceTrigger` | Keyword | `scheduled`, `manual`, `event`, ... |

Then the Temporal UI answers it with a query such as `TableUuid = "<uuid>" AND ExecutionStatus = "Running"`. Each workflow also gets a readable static summary (table name, operations). The console's table page links to the Temporal UI with that query filled in. The search attribute names live in the Temporal contracts and are pinned by a wire-name test like the signal names. This is built in milestone 1 and extended by each later milestone that adds a workflow.

## Verification and rebuilds

- Every milestone is verified against its goals on the minikube cluster, by forcing the rare event where needed (short timeout, oversized job, small budget). What cannot be verified is written as a risk on the milestone's issues; work moves on.
- At the end of each milestone the main session judges its size. Small: redeploy wave 25 only (`platform/25-lakehouse-control-plane/bootstrap.sh`). Large: `task offboard` then `task onboard` (KUBE_CONTEXT=retail-lakehouse, 8 CPUs, 26 GB), then the full e2e (`platform/25-lakehouse-control-plane/e2e.sh`), which must pass.
- The main session also judges whether the milestone's behaviour belongs in the e2e; if yes, it is added, keeping one Spark job at a time.

## Working process

- Milestones run in order 1 → 5. Each is implemented by one subagent that reads the Linear project P-KCL-6 and its milestone's issues, follows TDD, and posts progress, findings, decisions and blockers as comments on the issue they concern while it works.
- When it ends, the subagent reports to the main session what happened. The main session reads the issues, sets their status, runs a reviewer on the milestone's diff, gets findings fixed, verifies on the cluster, then starts the next milestone.
- Design details not settled here are decided by the subagent, with the reasoning in an issue comment; work does not stop to ask (the main session's call, 2026-11-13).
- Work happens on `main` with local commits only, no push (main session's call). Every commit passes `pytest`, `ty check`, `ruff check .`, `lint-imports` and follows the project rules (one object per file, DDD layering, StrEnum, ABC ports, `from __future__ import annotations`).
- After milestone 5, the main session writes a summary of all five milestones, with outcomes and open risks, as a comment on the Linear project.

## Left to the builder

Concrete S / M / L numbers, the small / recent filters' thresholds, N, the budget default, the priority weights, the pool idle period, table and column names, and how each piece is split into commits.
