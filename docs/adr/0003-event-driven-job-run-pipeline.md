# Event-driven Job → JobRun pipeline

Triggering a Job is split across three use cases connected by domain events through the outbox: `TriggerJobUseCase` mutates the **Job** aggregate (validates ACTIVE + active-runs ceiling, emits `JobTriggered`), `CreateJobRunUseCase` (handler on `JobTriggered`) creates a PENDING **JobRun** and emits `JobRunCreated`, `SubmitJobRunUseCase` (handler on `JobRunCreated`) hands the run to the runtime adapter matching `Job.runtime_kind`. Each use case touches exactly one aggregate; handlers must be idempotent because the outbox may redeliver.

## Considered Options

- **Same-transaction pipeline.** A single use case loads the Job, validates, creates the JobRun, and submits to the runtime in one DB transaction. Simpler and stronger atomicity guarantees. Rejected: spans two aggregates per transaction, couples scheduling code to runtime adapters, and a runtime-submit failure either rolls back the JobRun (losing the audit trail of "we tried") or leaks an inconsistent state.
- **JobRun created by the runtime adapter on submit.** Scheduler skips JobRun creation; the runtime callback creates it once it has a backend handle. Rejected: the PENDING window vanishes from the UI, and a runtime crash leaves no record that a trigger happened.
- **Event-driven pipeline** (chosen). Each step is its own aggregate's use case; the outbox is the integration backbone.

## Consequences

- Latency: a JobTriggered → JobRunCreated → SubmitJobRun chain has two hops of outbox dispatch. Acceptable for a maintenance workload (seconds-to-minutes scheduling, not real-time).
- Idempotency is mandatory. Each handler must tolerate redelivery — `CreateJobRunUseCase` keys on a deterministic run id derived from the trigger; `SubmitJobRunUseCase` checks the JobRun's status before submitting.
- Failure modes are surface-able as separate events: `JobTriggerSkipped`, `JobRunCreateFailed`, `JobRunSubmitFailed` each carry distinct reasons and can be retried or alerted on independently.
- The outbox publisher becomes load-bearing infrastructure for correctness, not just for downstream integrations. Outbox lag directly delays runs.
- Adding a new pre-submit step (e.g. cost estimation, approval) becomes a new handler on `JobRunCreated` — no aggregate or use case changes upstream.
