# 15. Ids are issued only by the domain

Date: 2026-11-24

Status: Accepted. Supersedes the `shared_kernel` paragraph of ADR 0011.

## Context

ADR 0011 gave every id the table maintenance context mints a type prefix and put the code that mints and checks them in `shared_kernel`, a stdlib-only package beside `base`. The package existed for one reason: the Temporal reconciliation workflow mints its run and reconciliation ids itself, and the workflow sandbox may not import `base` or Pydantic, so the minting code had to live somewhere both could reach.

That arrangement left the `mr-` prefix written in four places: the run id type, a table's recorded attempt (a string checked against its own copy of the pattern, because typing it as the run id made the table and run aggregate packages import each other), the workflow, and the k8s adapter that names Spark applications. `rc-` had a second copy in the workflow too. Every test compared against the strings its own file wrote down, so a copy that drifted would pass the unit tests and stop every scheduled maintenance on the cluster. The name also misled: a Shared Kernel in DDD (Evans) is a small part of the model two bounded contexts agree to share, not a utility package, and `base` was already described as the shared kernel. Linear KCL-99 asked for each id format to be defined once and issued only by the domain.

## Decision

- **The format lives in `base.EntityId`.** The base32 encoding, the prefix and suffix patterns and the minting are private functions of `base/entity_id.py`. `EntityId.new()` mints from `uuid.uuid7()`, `.suffix` is the part after `<PREFIX>-`, and `EntityId.is_shaped_like_an_id(text)` answers the one question other code asked of the any-prefix pattern (policy names must not look like ids). The format itself (TypeID suffix encoding, 2 to 8 lowercase letters of prefix) is unchanged from ADR 0011, and so is every stored and served id.
- **Id types sit in the shared domain model.** The table maintenance id types live in `application/domain/model/shared/`, so one aggregate names another by its typed id without the two packages importing each other. A table's recorded attempt holds a `TableMaintenanceRunId`. The catalog context's aggregates do not reference each other, so its id types stay where they are.
- **Adapters read ids through their ports.** The k8s adapter builds the `TableMaintenanceRunId` its port re-exports and names a Spark application by its `suffix`; the gateway input still carries the id as a string.
- **Workflows ask the application for ids.** The reconciliation workflow calls two local activities, `issue_reconciliation_id` and `issue_run_ids`, each wrapping an inbound port whose service calls the id type's `new()`. A local activity runs in the worker that runs the workflow, and Temporal records its result in the history, so a replay reads the same ids back. Issuing run ids is a step of its own before the activity that creates the runs: a create that stored its runs and failed before reporting would, on its retry, issue new ids and duplicate the runs, while a retried issue before its result is recorded only issues ids no run ever used.
- **`shared_kernel` is gone,** with its import-linter contract `shared-kernel-stdlib-only`; `base` imports nothing from the project, and `base` is described as the DDD building blocks.

## Consequences

- A new id kind is one class with a `PREFIX` in its context's shared domain model; nothing else copies its prefix, and tests check shapes by building the id type.
- Workflows can no longer mint ids at all: they import neither `base` nor the domain, so an id a workflow needs comes from an activity.
- A reconciliation pass makes two more local-activity calls. They add marker events to the history and need no round trip to the Temporal server.
- Workflows that started before the change cannot replay under the new code, which calls activities the old histories do not hold. During development no compatibility path is kept (KCL-110); the cluster is rebuilt instead.

## References

- ADR 0011, Prefixed resource ids.
- Eric Evans, *Domain-Driven Design*, chapter 14 (Shared Kernel).
- Temporal Python SDK documentation, local activities (`workflow.execute_local_activity`).
- TypeID specification: https://github.com/jetify-com/typeid
