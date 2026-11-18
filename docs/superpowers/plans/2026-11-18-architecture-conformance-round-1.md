# Architecture Conformance Round 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the backend closer to DDD / Clean Architecture / Ports & Adapters on four points: `base/` holds only building blocks (KCL-85), use-case nested types become nested classes (KCL-87), inbound port input/output use Pydantic (KCL-88), and Temporal activities are grouped per workflow (KCL-86). Every rule gets an architecture test.

**Architecture:** `base/` loses its Pydantic helpers (`validated_copy` becomes `ValueObject.with_changes`, `validation_message` becomes the `InvariantViolation` exception raised by the model bases, `WholeSeconds` moves into the table-maintenance domain) and gains `UseCaseInput` / `UseCaseOutput`. All 68 inbound ports migrate to those bases in aggregate batches, guarded by an architecture test whose pending list shrinks to empty. Activities are regrouped into one class per workflow contract package.

**Tech Stack:** Python 3.13, Pydantic v2, FastAPI, Temporal Python SDK, pytest, ty, ruff, import-linter.

**Spec:** Linear issues KCL-85, KCL-87, KCL-88, KCL-86 (project 架構符合預期, P-KCL-9). Their decisions are copied into Global Constraints below; the issue text is the authority where this plan is silent.

## Global Constraints

- Backend root: `src/data-platform/backend`. Run everything as `uv run --project src/data-platform/backend --directory src/data-platform/backend <cmd>`; never `cd`.
- Every commit passes `pytest -q`, `ty check`, `ruff check .`, `lint-imports`. TDD: failing test first.
- Commits: conventional (`refactor(backend):`, `docs(adr):` …), explicit paths only, never `--no-verify`, body ends with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- One object per file; `from __future__ import annotations`; ABC over Protocol; StrEnum.
- `base` public names must come from this allowlist (not all need to exist): `ValueObject`, `Entity`, `EntityId`, `AggregateRoot`, `DomainEvent`, `InvariantViolation`, `Specification`, `Repository`, `Store`, `Gateway`, `UseCase`, `UseCaseInput`, `UseCaseOutput`, `EventHandler`, `EventDispatcher`, `UnitOfWork`. Do not create `Specification` or `UnitOfWork`.
- `UseCaseInput` / `UseCaseOutput`: Pydantic, `frozen=True`, `strict=True`, `extra="forbid"`; fields hold primitives and stdlib types only (`str`, `int`, `float`, `bool`, `None`, `datetime`, `timedelta`, `list`, `tuple`, `dict`, nested classes of the same file), never a domain type.
- Nested types are nested classes named by what they are (`ListTableCommitsUseCaseOutput.Commit`, `PlanTableMaintenanceUseCaseOutput.Check`); at most one nesting level; each `input.py` / `output.py` has exactly one top-level class; `__init__.py` exports only `{Name}UseCase`, `{Name}UseCaseInput`, `{Name}UseCaseOutput`.
- External formats do not change: REST bodies (the console OpenAPI contract test must stay green), the settings JSON in PostgreSQL, Temporal payloads, the Spark request.
- Temporal activity names (`test_wire_names.py`) never change; only their location moves.
- Do not touch `.claude/worktrees/`, `.claude/settings*.json`, or the on-hold paths in the root `CLAUDE.md`.

## Review Focus

1. **A Temporal payload changes shape** (datetime written `…Z` instead of `+00:00`, a key renamed, a tuple becoming a list in a different place): in-flight workflows break. Pinned by Task 5's golden test that `activity_payload` gives the same dict for a Pydantic output as the old `asdict` path did.
2. **Strict mode refuses a dict that used to work** when an activity or the event consumer builds an input from a Temporal or Kafka payload (ISO datetime strings, JSON arrays for tuples). Pinned by each migration task building every activity-fed input from a recorded payload through `from_primitives`.
3. **A broken invariant stops answering 422 with the same one-line message** once `validation_message` is gone. Pinned by Task 3's test through the web app for both contexts.
4. **An entity assignment or `from_primitives` call still leaks a raw `pydantic.ValidationError`** past the model bases. Pinned by Task 3's tests on all three construction paths.
5. **The console API changes unnoticed** (a response field order, nullability or name). Pinned by Task 11 running `task dev:generate-api` with no diff and `task gates:pre-pr` (contract test).

---

### Task 1: `ValueObject.with_changes` replaces `validated_copy`

**Files:**
- Modify: `base/value_object.py`, `base/__init__.py`
- Delete: `base/validated_copy.py`, `tests/base/test_validated_copy.py`
- Modify (callers): `context/table_maintenance/application/domain/model/table/operation_state.py`, `context/table_maintenance/application/domain/model/table_maintenance_run/table_maintenance_run.py`, `context/table_maintenance/application/domain/service/table/assess_maintenance.py`, and the tests and fakes that import `validated_copy` (grep)
- Modify: `tests/architecture/test_domain_models_complete.py` (its `model_copy` guard message and docstring point at `with_changes`)
- Test: `tests/base/test_value_object.py`

**Interfaces:**
- Produces: `ValueObject.with_changes(self, **changes: object) -> Self`. It runs every field and model validator on the changed copy and raises `TypeError` naming the class for an unknown field (the current `validated_copy` behaviour, moved).

- [ ] **Step 1:** Move the `validated_copy` tests into `tests/base/test_value_object.py` as `test_with_changes_*`, keeping the same assertions:
  - a changed copy;
  - a validator that rejects the change;
  - the unknown field `TypeError`;
  - the original left unchanged.
- [ ] **Step 2:** Run `pytest tests/base/test_value_object.py -q`. Expected: FAIL, `with_changes` is not defined.
- [ ] **Step 3:** Implement `with_changes` on `ValueObject`. Replace every `validated_copy(x, …)` with `x.with_changes(…)`. Test fakes that copy aggregates (catalog `in_memory_*_repo.py`) rebuild the aggregate with `type(x).model_validate({**x.model_dump(), **changes})` locally, because aggregates are never copied in domain code. Delete `base/validated_copy.py` and drop it from `base/__init__.py`.
- [ ] **Step 4:** Run the full suite plus `ty check`, `ruff check .` and `lint-imports`. Expected: all pass, and `grep -rn validated_copy src/data-platform/backend` finds nothing.
- [ ] **Step 5:** Commit `refactor(base): copy value objects with ValueObject.with_changes`.

### Task 2: `WholeSeconds` moves into the table-maintenance domain

**Files:**
- Create: `context/table_maintenance/application/domain/model/shared/whole_seconds.py` (content of `base/whole_seconds.py`)
- Delete: `base/whole_seconds.py`
- Move: `tests/base/test_whole_seconds.py` → `tests/context/table_maintenance/application/domain/model/shared/test_whole_seconds.py`
- Modify: `positive_duration.py`, `non_negative_duration.py`, `remove_orphan_files_execution_policy.py`, `domain/model/shared/__init__.py`, `base/__init__.py`, and `tests/base/test_value_object.py` (which uses `WholeSeconds` only as a sample field; use a plain `int` there or import from the new place)

**Ruling (recorded on KCL-85):** It stays an `Annotated` type rather than becoming a value object. A value object would change every duration field's shape in the domain for no gain, and the wire form must stay integer seconds.

- [ ] **Step 1:** Move the test file and change its import to `from context.table_maintenance.application.domain.model.shared import WholeSeconds`. Run it. Expected: FAIL (ImportError).
- [ ] **Step 2:** Move the module, re-export it from `domain/model/shared/__init__.py`, and update the three users plus `base/__init__.py`.
- [ ] **Step 3:** Run the full suite and the three checkers. Expected: all pass, and `grep -rn "from base import.*WholeSeconds"` finds nothing.
- [ ] **Step 4:** Commit `refactor(table-maintenance): own the WholeSeconds duration type`.

### Task 3: `InvariantViolation` replaces `validation_message`

**Files:**
- Create: `base/invariant_violation.py`
- Modify: `base/value_object.py`, `base/entity.py`, `base/entity_id.py`, `base/aggregate_root.py` (only if it overrides construction), `base/domain_event.py`, `base/__init__.py`
- Delete: `base/validation_message.py`, `tests/base/test_validation_message.py`
- Modify (callers): `context/table_maintenance/application/service/shared/translate_domain_errors.py`; `context/catalog/application/service/catalog/{update_catalog,catalog_id_from_name,connection_config_from_request,storage_config_from_request}.py`; `tests/context/catalog/application/domain/model/catalog/test_catalog_config_primitives.py`
- Test: `tests/base/test_invariant_violation.py`, plus one web test per context (see Step 1)

**Interfaces:**
- Produces: `class InvariantViolation(ValueError)`. It is constructed with a one-line `message: str`, and `str(exc) == message`. It also has the classmethod `InvariantViolation.from_error(exc: ValueError) -> InvariantViolation`, which builds that line exactly as `validation_message` did:
  - the first Pydantic error as `"<dotted.loc>: <msg>"`;
  - just `<msg>` for a model-level error;
  - the `"Value error, "` prefix stripped;
  - `str(exc)` for a non-Pydantic error.
- Produces: every construction path of the model bases raises `InvariantViolation`, never a raw `pydantic.ValidationError`. The paths are keyword construction, `EntityId("…")`, `from_primitives`, `model_validate` / `model_validate_json`, and `Entity` assignment (`validate_assignment`). It is chained with `from` the original error.

- [ ] **Step 1:** Write the failing tests.
  - Move the `validation_message` message-format cases into `tests/base/test_invariant_violation.py` as `InvariantViolation.from_error` cases.
  - Add `test_value_object_construction_raises_invariant_violation`, `test_from_primitives_raises_invariant_violation`, `test_entity_assignment_raises_invariant_violation` and `test_entity_id_raises_invariant_violation`. Each asserts `pytest.raises(InvariantViolation)`, the one-line message, and that `isinstance(exc, pydantic.ValidationError)` is False.
  - Add one web-level test per context: a request breaking an invariant answers 422 with the same `detail` text it has today. For table maintenance, a policy with `cooldown_seconds: 0`; for catalog, an invalid catalog name. Read the current detail first and pin that text.
- [ ] **Step 2:** Run the new tests. Expected: FAIL.
- [ ] **Step 3:** Implement `InvariantViolation`, and wrap the construction paths in the bases.
  - Override `__init__`, `model_validate`, `model_validate_json` and, on `Entity`, `__setattr__`.
  - Catch only `pydantic.ValidationError`.
  - An `InvariantViolation` raised inside a nested validator arrives wrapped by Pydantic, and must still come out as one `InvariantViolation` carrying the inner message.
- [ ] **Step 4:** Replace `validation_message(exc)` with `str(exc)` in the five callers, delete `base/validation_message.py` and drop it from `base/__init__.py`. Existing `except ValueError` blocks keep working, because `InvariantViolation` is a `ValueError`.
- [ ] **Step 5:** Run the full suite and the three checkers. Expected: all pass.
- [ ] **Step 6:** Commit `refactor(base): raise InvariantViolation from the model bases`.

### Task 4: `base/` allowlist test and docs

**Files:**
- Create: `tests/architecture/test_base_building_blocks.py`
- Modify: `base/__init__.py` (module docstring lists only what exists), `src/data-platform/backend/CLAUDE.md` (DDD Base Types section: no `WholeSeconds` / `validated_copy` / `validation_message`; add `with_changes`, `InvariantViolation`, the allowlist rule and "to add to `base`, edit the allowlist and say why here"), `docs/adr/0009-pydantic-in-the-domain-model.md` (Consequences bullet on copying now names `ValueObject.with_changes`; add a dated note)

- [ ] **Step 1:** Write the tests:
  - `test_base_exports_only_building_blocks`: `set(base.__all__) <= ALLOWED`, using the Global Constraints list.
  - `test_base_modules_define_nothing_public_outside_the_allowlist`: an AST scan of every `base/*.py` except `_`-prefixed modules; every public top-level class, function or assignment must be in `ALLOWED`.
  - `test_allowlist_rejects_an_extra_name`: feed the checker function a fake source that defines `helper()` and assert it is reported. This proves the guard bites.
- [ ] **Step 2:** Run them. Expected: PASS, since Tasks 1–3 already emptied `base/`. If one fails, fix `base/`, not the test.
- [ ] **Step 3:** Update the docs listed above.
- [ ] **Step 4:** Run the full suite and the three checkers, then commit `test(architecture): allow only building blocks in base` together with the doc changes (or `docs(backend):` as a second commit).

### Task 5: `UseCaseInput` / `UseCaseOutput`, ADR 0010, the port contract and the migration guard

**Files:**
- Create: `base/use_case_input.py`, `base/use_case_output.py`
- Create: `docs/adr/0010-pydantic-in-inbound-ports.md`
- Create: `tests/architecture/test_inbound_port_models.py`
- Modify: `base/__init__.py`, `.importlinter` (contract `application-outer-rings-pydantic-free`), `context/table_maintenance/adapter/hybrid/temporal/inbound/activities/activity_payload.py`
- Test: `tests/base/test_use_case_input.py`, `tests/base/test_use_case_output.py`, `tests/context/table_maintenance/adapter/hybrid/temporal/inbound/activities/test_activity_payload.py`

**Interfaces:**
- Produces: `class UseCaseInput(BaseModel)` with the Global Constraints config and `@classmethod from_primitives(cls, data: Mapping[str, Any]) -> Self`, which validates in strict JSON mode like `ValueObject.from_primitives`. ISO strings become `datetime`, JSON arrays become `tuple` fields, and a non-JSON value raises `ValueError`.
- Produces: `class UseCaseOutput(BaseModel)` with the same config. Each gets an inheritance-depth guard of 1, like `ValueObject`.
- Produces: `activity_payload(output)` accepts a `UseCaseOutput` (via `model_dump()`, then the existing `_primitive` pass, so datetimes stay `datetime.isoformat()`) and, until Task 11, a dataclass.
- Produces: `PENDING_PORTS: frozenset[str]` in `test_inbound_port_models.py`, holding every use-case directory not yet migrated as `"<context>/<aggregate>/<use_case>"`. Tasks 6–10 delete their entries.

- [ ] **Step 1:** Write the failing tests:
  - base tests: strict (an int field refuses `"1"`), frozen, extra keys rejected, and `from_primitives` reading an ISO datetime and a list into a tuple field;
  - `test_activity_payload_matches_dataclass_payload`: the same values as a dataclass and as a `UseCaseOutput` with a UTC `datetime` give identical dicts, including the `+00:00` offset text;
  - in `test_inbound_port_models.py`, for every use-case directory not in `PENDING_PORTS`:
    - `input.py` (when present; no-input use cases have none) / `output.py` each define exactly one top-level class, which subclasses `UseCaseInput` / `UseCaseOutput`;
    - nested classes are at most one level deep, and each subclasses the same base;
    - the files import nothing from `*.application.domain`;
    - `__init__.py` exports exactly the three names.
  - `test_pending_ports_exist`: every `PENDING_PORTS` entry is a real directory, so a stale entry fails.
  - Start `PENDING_PORTS` with all 68 directories (generate the list with a one-off script; paste it sorted).
- [ ] **Step 2:** Run. Expected: the base and payload tests FAIL, and the guard passes because everything is pending.
- [ ] **Step 3:** Implement the two bases and the `activity_payload` change. Ports reach Pydantic only through `base` (`allow_indirect_imports = true`), so contract `application-outer-rings-pydantic-free` stays as it is: `service`, `port` and `exceptions` still never import `pydantic` directly. Confirm with `lint-imports`.
- [ ] **Step 4:** Write ADR 0010, which partly supersedes 0009's "Services stay free of Pydantic":
  - inbound port input and output subclass `UseCaseInput` / `UseCaseOutput`;
  - why: Hombergs' self-validating input model, and one validation path for the web, Temporal and Kafka entry points;
  - primitives only;
  - services still never import Pydantic.

  Add a status line to ADR 0009 pointing at 0010.
- [ ] **Step 5:** Run the full suite and the three checkers, then commit `feat(base): add UseCaseInput and UseCaseOutput for inbound ports`.

### Tasks 6–10: migrate the inbound ports, one batch per task

Each task migrates every use case in its batch and nothing else:

| Task | Batch |
|---|---|
| 6 | catalog: `catalog` (5), `namespace` (5), `view` (4), `generic_table` (4) |
| 7 | catalog: `table` (8) |
| 8 | table_maintenance: `table` (10) |
| 9 | table_maintenance: `table_maintenance_run` (9), `table_reconciliation` (2), `compaction_candidate` (2) |
| 10 | table_maintenance: `table_maintenance_policy` (7), `table_maintenance_policy_attachment` (4), `table_discovery_rules` (3), `compaction_round` (5) |

**Files (per use case):** `application/port/inbound/<aggregate>/<use_case>/{input,output,__init__}.py`, its service under `application/service/<aggregate>/`, and every caller:
- web routers and DTO mappers under `adapter/inbound/web/<aggregate>/`;
- Temporal activities under `adapter/hybrid/temporal/inbound/activities/`;
- the event consumer under `adapter/inbound/event_consumer/`;
- outbound adapters that call another context's use case (catalog ← table_maintenance anti-corruption adapters);
- `bootstrap/`;
- the tests and fakes.

**Interfaces:**
- Consumes: `UseCaseInput`, `UseCaseOutput` and `activity_payload` from Task 5.
- Produces: each migrated use case's input and output, with nested classes named by what they hold. Field names do not change. Name nested classes after the resource, singular and in CamelCase: the item of `ListTablesUseCaseOutput` is `ListTablesUseCaseOutput.Table`, and the five extra types of `PlanTableMaintenanceUseCaseOutput` are `.Filter`, `.CandidatePartition`, `.Operation` (was `…OutputItem`), `.Measurement` and `.Check`. When the obvious name collides with a domain class imported in the same caller, the nested name still wins; the caller qualifies it.

- [ ] **Step 1:** Delete the batch's entries from `PENDING_PORTS`. Run `pytest tests/architecture/test_inbound_port_models.py -q`. Expected: FAIL for every use case in the batch.
- [ ] **Step 2:** For every entry point that builds one of these inputs from a dict (Temporal activity, event consumer), add or extend a test that builds the input with `{Name}UseCaseInput.from_primitives(payload)`. Use a payload copied from what the workflow or consumer sends today, read from the workflow code or an existing test fixture. Run it. Expected: FAIL.
- [ ] **Step 3:** Migrate:
  - subclass the bases and turn `…Item` classes into nested classes;
  - export only the three names;
  - switch dict-fed construction to `from_primitives`;
  - build outputs by keyword in services (strict mode: pass the declared sequence type);
  - fix callers and tests.

  Behaviour, REST bodies and Temporal payloads stay identical.
- [ ] **Step 4:** Run the full suite and the three checkers. Expected: all pass.
- [ ] **Step 5:** Commit `refactor(<context>): migrate <aggregates> inbound ports to Pydantic`.

### Task 11: finish the port migration

**Files:**
- Modify: `tests/architecture/test_inbound_port_models.py` (remove `PENDING_PORTS` and `test_pending_ports_exist`; the guard now covers every use case), `activity_payload.py` (drop the dataclass path and `asdict` import), `tests/architecture/test_inbound_port_structure.py` (drop `test_output_classes_prefixed` and any `…Item` allowance that the new guard supersedes), `src/data-platform/backend/CLAUDE.md` (DTO naming table: no `UseCaseOutputItem`; inbound input/output subclass `UseCaseInput` / `UseCaseOutput`, nested classes by noun; the Rules bullet about Pydantic now cites ADR 0010), `docs/agents/project-history.md` (one 2026-11-18 line covering KCL-85, 87, 88)

- [ ] **Step 1:** Remove `PENDING_PORTS`. Run the guard. Expected: PASS, or it names whatever a batch missed; fix that port.
- [ ] **Step 2:** Make the cleanup edits above.
- [ ] **Step 3:** Run the full suite and the three checkers. Then run `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` and confirm `git status` shows no change under the frontend's generated client. Then run `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr` once. Expected: all green, no generated-client diff.
- [ ] **Step 4:** Commit `refactor(backend): finish moving inbound ports to Pydantic` (plus `docs:` for the docs if separate).

### Task 12: one activities class per workflow (KCL-86)

**Files:**
- Modify: `context/table_maintenance/adapter/hybrid/temporal/inbound/activities/{table_reconciliation_activities,table_maintenance_activities}.py`, `activities/__init__.py`, `bootstrap/container/build_activities.py` (and the `Activities` holder it fills), the worker registration that lists activity methods
- Delete: `activities/workflow_signal_activities.py` (its methods move)
- Create: `tests/architecture/test_temporal_activity_grouping.py`
- Modify: the activity tests that construct these classes; `src/data-platform/backend/CLAUDE.md` (hybrid temporal paragraph: one activities class per workflow contract package, the signal-wiring exception)

**Interfaces:**
- Produces:
  - `TableReconciliationActivities` holds `PLAN_TABLE_MAINTENANCE`, `RECORD_TABLE_RECONCILIATION`, `RELEASE_COMPACTION_CANDIDATES` and `GET_WORKFLOW_RUNNING`.
  - `TableMaintenanceActivities` holds `CREATE_MAINTENANCE_RUN`, `RECORD_MAINTENANCE_OPERATION_RESULT`, `SUBMIT_MAINTENANCE_OPERATION`, `GET_MAINTENANCE_JOB_STATUS`, `DELETE_MAINTENANCE_JOB`, `GET_MAINTENANCE_JOB_PODS`, `SIGNAL_ADMISSION_ACQUIRE` and `SIGNAL_PARENT`.
  - `TableDiscoveryActivities` and `CompactionRoundActivities` are unchanged.
  - Constructor arguments follow the methods. `TableMaintenanceActivities` takes the Temporal `Client` and the admission settings; `TableReconciliationActivities` takes the `Client`. The callback URL, attempt deadline and max attempts go wherever their methods land.
- `SIGNAL_EXCEPTIONS = {"SIGNAL_ADMISSION_ACQUIRE", "SIGNAL_PARENT", "GET_WORKFLOW_RUNNING"}`: the activities that call the Temporal client instead of an inbound port.

- [ ] **Step 1:** Write `test_temporal_activity_grouping.py`:
  - `test_activity_lives_in_its_workflows_class`: an AST scan of `activities/*.py`. For every `@activity.defn(name=<Enum>.<MEMBER>)`, the enum class `XActivity` maps to the class `XActivities` (for example, `TableMaintenanceActivity` maps to `TableMaintenanceActivities`), and the method must sit in that class.
  - `test_activity_calls_one_inbound_port`: every decorated method not in `SIGNAL_EXCEPTIONS` contains exactly one `self._<name>.execute(` call.
  - `test_one_activities_class_per_activity_enum`: the set of `*Activities` classes equals the set of `contracts/*/activity.py` enums with the suffix swapped.
- [ ] **Step 2:** Run. Expected: FAIL on the misplaced methods.
- [ ] **Step 3:** Move the methods, delete `workflow_signal_activities.py`, and update the `__init__` exports, `build_activities.py`, the worker registration and the tests. Activity names are unchanged.
- [ ] **Step 4:** Run the full suite and the three checkers, including `test_wire_names.py`. Expected: all pass.
- [ ] **Step 5:** Commit `refactor(table-maintenance): group Temporal activities by workflow`, plus the `CLAUDE.md` edit and a project-history line for KCL-86.

### Task 13 (controller): verify on minikube

Not dispatched to a subagent. The controller:
1. builds and deploys the backend image (`minikube-deploy` skill, `KUBE_CONTEXT=retail-lakehouse`);
2. runs `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh`;
3. at its discretion, as the user allowed, does `task offboard` / `task onboard` and runs e2e again;
4. marks KCL-85..88 Done in Linear with a comment each, including the Task 2 ruling on KCL-85.
