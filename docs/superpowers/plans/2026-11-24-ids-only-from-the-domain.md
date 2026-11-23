# Ids Only From the Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every id format is defined once, in `base.EntityId` and the domain id types, and only the domain issues ids; the `shared_kernel` package goes away.

**Architecture:** The `table_maintenance` id types move to `domain/model/shared/`, so aggregates reference each other by typed ids without import cycles. The k8s adapter reads the run id type through its port. The reconciliation workflow asks the application for new ids through a local activity, whose result Temporal records, instead of minting them itself. The prefixed-id code then folds into `base/entity_id.py` as private functions.

**Tech Stack:** Python 3.14, Pydantic v2, Temporal Python SDK, import-linter, pytest.

**Spec:** Linear KCL-99 ("id 只由 domain 定義和產生，拿掉 shared_kernel 套件"), its four steps and its completion conditions.

## Global Constraints

- The id format, prefixes, API and stored values do not change; the alphabet stays TypeID base32 (only function names change).
- No compatibility code during development (KCL-110): no `workflow.patched` branch, no replay fixture for old histories; the cluster is rebuilt instead.
- `adapters-see-only-ports`: adapters take id types from port re-exports.
- Gateway inputs carry primitives only: `SubmitMaintenanceJobGatewayInput.run_id` stays `str`.
- One primary object per file; private helpers may live in `entity_id.py`.
- import-linter has no exceptions; `shared` is an allowed aggregate-axis directory.
- The id-issuing local activity is not merged with the run-creating activity.

## Review Focus

- A stored table row whose `last_recorded.run_id` was written before the change must read back to an equal `RecordedAttempt`.
- A workflow replay must issue the same ids: the ids come from the recorded local-activity result, not from anything the workflow computes.
- The Spark application name for a run must stay byte-identical (`tm-<code>-<suffix>-a<n>`).
- A policy name shaped like an id of any prefix must still be refused after `any_prefixed_id_pattern` goes.
- The TypeID spec vectors must still pass through `EntityId.new()`.

---

### Task 1: Id types in `domain/model/shared/`

Move `TableId`, `TableMaintenanceRunId`, `TableReconciliationId`, `TableMaintenancePolicyId`, `TableMaintenancePolicyAttachmentId`, `TableDiscoveryPolicyId`, `TableDiscoveryPolicyAttachmentId`, `TableDiscoveryRuleId` and `CatalogDiscoveryId` (their `*_id.py` files) to `context/table_maintenance/application/domain/model/shared/`, exported from that package; the aggregate packages stop exporting them and every import site imports them from `domain.model.shared` (ports keep re-exporting them). `DEFAULT_POLICY_ID`, `DEFAULT_DISCOVERY_POLICY_ID` and `UnknownDiscoveryRuleId` stay with their policies. `RecordedAttempt.run_id` becomes `TableMaintenanceRunId`.

- [ ] Test first: `test_a_recorded_attempt_holds_a_run_id` (in the table tests) asserts `type(RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=1).run_id) is TableMaintenanceRunId`, and a malformed id raises `InvariantViolation` matching `TableMaintenanceRunId must look like mr-`. A table-row round trip test asserts the stored JSON keeps `"run_id": "mr-…"`.
- [ ] Run, watch the first fail; move the files, rewrite imports, change the field; run the suite, ty, ruff, lint-imports.
- [ ] Commit `refactor(domain): table maintenance ids live in the shared domain model (KCL-99)`.

### Task 2: The k8s adapter uses the run id type

`spark_application_name` takes the run id type from `application.port.outbound.table_maintenance_run`, checks the string by building it, and takes the suffix from a new `EntityId.suffix` property (the part after `<PREFIX>-`; `TypeError` for an id kind with no `PREFIX`).

- [ ] Test first: `test_suffix_is_the_part_after_the_prefix` and `test_suffix_needs_a_prefix` in `tests/base/test_entity_id.py`; the existing Spark application name tests stay as they are.
- [ ] Implement; run; commit `refactor(adapter): the Spark application name reads the run id type (KCL-99)`.

### Task 3: The workflow asks for ids through a local activity

New inbound port in the `table_reconciliation` aggregate, `IssueTableReconciliationIdsUseCase` (input `run_count: NonNegativeInt`, output `reconciliation_id: str`, `run_ids: list[str]`), whose service calls `TableReconciliationId.new()` once and `TableMaintenanceRunId.new()` `run_count` times. New activity name `TableReconciliationActivity.ISSUE_IDS = "table_reconciliation.issue_ids"` (pinned in `test_wire_names.py`), a `TableReconciliationActivities.issue_ids` method, and the workflow calls it with `workflow.execute_local_activity` where it now mints: once with `run_count=0` for the reconciliation id, once with the plan's operation count for the run ids. `mint_workflow_prefixed_id.py`, `_RUN_ID_PREFIX` and `_RECONCILIATION_ID_PREFIX` go.

- [ ] Test first: service test (prefixes, count, distinct), activity test (dict in, dict out), wire-name test, workflow tests that the ids the workflow uses are the ones the local activity returned.
- [ ] Implement; run; commit `refactor(temporal): the reconciliation workflow takes its ids from the application (KCL-99)`.

### Task 4: No `shared_kernel`

Fold the prefixed-id code into `base/entity_id.py` as private functions (`_encode_base32`, the prefix and suffix patterns); `prefixed_id_from_parts` goes. `checked_policy_name` uses a new `EntityId.is_shaped_like_an_id(text) -> bool` (any prefix). Remove the `shared-kernel-stdlib-only` contract, adjust `base-isolation` and `temporal-workflows-sandbox-safe`, and update the architecture tests, the isort first-party list, the backend `CLAUDE.md` (no Shared Kernel section; `base` is "DDD building blocks"), ADR 0015 superseding ADR 0011's shared-package paragraph, and `project-history.md`.

- [ ] Test first: the TypeID spec vectors move to `tests/base/test_entity_id.py` and run through `EntityId.new()` with `uuid.uuid7` replaced; `test_is_shaped_like_an_id`.
- [ ] Implement; run the suite, ty, ruff, lint-imports; commit `refactor(base): prefixed ids live in EntityId and shared_kernel goes (KCL-99)`.
