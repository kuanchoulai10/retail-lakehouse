# Pydantic Domain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the backend domain model from dataclasses to Pydantic v2 and replace the hand-written settings and catalog-config converters with `from_primitives` / `to_primitives`, without changing any external format.

**Architecture:** Pydantic base types are added beside the dataclass ones in a temporary package `base.model` (same class names), so each aggregate migrates in its own green commit; a dataclass subclass cannot inherit a Pydantic base, which rules out an in-place switch. The last task deletes the dataclass bases, moves `base.model` up into `base`, and rewrites `from base.model import` to `from base import`. The domain may import only the stdlib, `base`, its own domain, and Pydantic, enforced by an allow-list test.

**Tech Stack:** Python 3.14, Pydantic 2.12.5 (already locked), pytest, ty, ruff, import-linter.

**Spec:** `docs/superpowers/specs/2026-11-10-pydantic-domain-model-design.md`

## Global Constraints

- Backend commands run as `uv run --project src/data-platform/backend --directory src/data-platform/backend <tool>`; never `cd`. Every commit passes `pytest -q`, `ty check`, `ruff check .`, `lint-imports` there.
- Domain and `base` import only: the stdlib (`sys.stdlib_module_names`), `__future__`, `base`, `context.<same context>.application.domain`, `pydantic`, `pydantic_core`, `annotated_types`.
- External formats are byte-for-byte unchanged: REST bodies, the settings JSON column in PostgreSQL, Temporal payloads, the Spark `GLAC_REQUEST` env. Durations are integer seconds on the wire under `*_seconds` keys and `timedelta` in the domain; a non-whole-second duration is rejected when encoded.
- `ValueObject` and `DomainEvent`: `frozen=True`, `strict=True`, `extra="forbid"`. `Entity` / `AggregateRoot`: `strict=True`, `extra="forbid"`, `validate_assignment=True`. `EntityId`: `RootModel[str]`, frozen, strict, positional construction kept.
- A broken invariant at construction raises Pydantic's `ValidationError`; the API answers 422 with a one-line message. `InvalidTableTransition` and `InvalidRunTransition` stay and still answer 409.
- Domain code never calls `model_copy`; a changed copy goes through `base.validated_copy`.
- One object per file, `from __future__ import annotations`, ABC not Protocol, StrEnum, TDD, conventional lowercase commit subjects ending with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. No YAML comments. Port DTOs, Temporal contracts, web DTOs and `StrEnum`s are out of scope.

## Review Focus

- Settings rows already in PostgreSQL decode to the same `MaintenanceSettings` and re-encode to the same JSON (Task 3, golden test).
- A request with `true` where an integer is expected, an unknown key, or `1.5` seconds still answers 422 with a one-line message (Task 3).
- An adapter that passes a `list` to a `tuple` field, or a plain string to an enum field, fails under strict mode at runtime, not at import (each aggregate task's adapter round-trip step).
- A copy-with-change that skips validation (`model_copy`) silently admits an invalid object (Task 2 architecture test).
- Moving `TYPE_CHECKING`-only imports to runtime for field annotations can introduce an import cycle or a model that is "not fully defined" only at first construction (Task 2 architecture test, applied in every later task).

---

### Task 1: Allow Pydantic, and only Pydantic, in the domain

**Files:**
- Create: `docs/adr/0009-pydantic-in-the-domain-model.md`
- Create: `src/data-platform/backend/tests/architecture/test_domain_dependencies.py`
- Modify: `src/data-platform/backend/.importlinter` (contracts `domain-pure`, `application-no-outer-rings`; new contract `application-outer-rings-pydantic-free`)
- Modify: `src/data-platform/backend/tests/architecture/test_importlinter_config.py` (if it lists contract names)
- Modify: `src/data-platform/backend/CLAUDE.md:77`, `docs/agents/known-follow-ups.md:67`, `docs/adr` row in root `CLAUDE.md`

**Interfaces:**
- Produces: the dependency rule every later task relies on; no code.

- [ ] **Step 1: Write the failing allow-list test.** `test_domain_imports_only_allowed_modules` parses every `.py` under `base/` and `context/*/application/domain/` with `ast` and fails, listing `file: module`, for any import whose top-level name is outside the allowed set in Global Constraints, or any `context.*` import outside the file's own context's `application.domain`. Add `test_allow_list_rejects_a_third_party_import`, which runs the same checker on the source string `"import httpx\n"` and asserts one violation, and `test_allow_list_accepts_pydantic`, which asserts none for `"from pydantic import BaseModel\n"`.
- [ ] **Step 2: Run** `pytest tests/architecture/test_domain_dependencies.py -v`. Expected: the two checker tests fail until the checker exists, then pass; the repository scan passes (no domain file imports Pydantic yet).
- [ ] **Step 3: Change the contracts.** Remove `pydantic` from `domain-pure` and from `application-no-outer-rings`. Add `[importlinter:contract:application-outer-rings-pydantic-free]`, type `forbidden`, sources `context.*.application.service`, `context.*.application.port`, `context.*.application.exceptions`, forbidden `pydantic`, `allow_indirect_imports = true` (services reach Pydantic only through the domain). Update `test_importlinter_config.py` if it pins the contract list.
- [ ] **Step 4: Write ADR 0009** (Context, Decision, Consequences) from the spec's Decisions table, and change the backend `CLAUDE.md` rule to: "Domain depends only on the stdlib, `base` and Pydantic (`pydantic`, `pydantic_core`, `annotated_types`). Enforced by `test_domain_dependencies.py` (allow-list) and contract `domain-pure`." Replace the known-follow-up line with a pointer to this plan; add `0009 pydantic in the domain` to the ADR list in the root `CLAUDE.md`.
- [ ] **Step 5: Verify** with the four commands in Global Constraints. Expected: all pass, `Contracts: 15 kept, 0 broken`.
- [ ] **Step 6: Commit** `refactor(backend): allow only pydantic as a domain dependency`.

### Task 2: Pydantic base types in `base.model`

**Files:**
- Create: `src/data-platform/backend/base/model/__init__.py`, `value_object.py`, `entity_id.py`, `entity.py`, `aggregate_root.py`, `domain_event.py`, `whole_seconds.py`, `validated_copy.py`, `validation_message.py`
- Create: `src/data-platform/backend/tests/base/model/test_value_object.py`, `test_entity_id.py`, `test_entity.py`, `test_aggregate_root.py`, `test_domain_event.py`, `test_whole_seconds.py`, `test_validated_copy.py`, `test_validation_message.py`
- Create: `src/data-platform/backend/tests/architecture/test_domain_models_complete.py`
- Modify: `src/data-platform/backend/pyproject.toml` (`runtime-evaluated-base-classes`), `tests/architecture/aggregates.py`, `tests/architecture/test_inheritance_depth.py`

**Interfaces:**
- Produces (`from base.model import …`):
  - `ValueObject(BaseModel)`, config per Global Constraints; `@classmethod from_primitives(cls, data: Mapping[str, Any]) -> Self` validates in JSON mode (`model_validate_json(json.dumps(data))`) so enums and `WholeSeconds` accept their wire values while strict mode still rejects `true` for an int; `to_primitives(self) -> dict[str, Any]` is `model_dump(mode="json", by_alias=True)`.
  - `EntityId(RootModel[str])`; `TableId("x")` works; `.value -> str` property; `str(id)` is the value; equal only to the same subclass with the same value; hashable.
  - `Entity[ID: EntityId](BaseModel)`; `__eq__` / `__hash__` by `id` and class.
  - `AggregateRoot[ID: EntityId](Entity[ID])`; `register_event(event: DomainEvent) -> None`, `collect_events() -> list[DomainEvent]`; events in a `PrivateAttr`, never dumped or compared.
  - `DomainEvent(BaseModel)`; `occurred_at: datetime` defaults to now in UTC.
  - `WholeSeconds = Annotated[timedelta, …]`: accepts a `timedelta`, or an `int` (not `bool`) as seconds; serializes in JSON mode to `int`; raises `ValueError` when serializing a non-whole-second value.
  - `validated_copy[M: BaseModel](model: M, /, **changes: object) -> M`: a copy with `changes` applied that runs all validators; an unknown field name raises.
  - `validation_message(exc: ValueError) -> str`: for a Pydantic `ValidationError`, the first error as `"<dotted.loc>: <msg>"` with Pydantic's `"Value error, "` prefix removed (no loc part for a model-level error); otherwise `str(exc)`.
  - Every class keeps `enforce_max_depth(cls, <base>, 1)` in `__init_subclass__`.

- [ ] **Step 1: Prove the toolchain first.** Write `tests/base/model/test_entity_id.py::test_positional_construction_type_checks` constructing `class _Id(EntityId)` as `_Id("a")`, and a two-field `ValueObject` subclass by keyword, then run `ty check` on the test file. Expected after Step 3: no diagnostics. If `ty` cannot type Pydantic constructors or `RootModel` positional construction, stop and report BLOCKED with the diagnostics; do not add ignores.
- [ ] **Step 2: Write the failing base tests**, one file per object, asserting at least: frozen value object rejects assignment; `extra="forbid"` rejects an unknown key; strict rejects `True` for an `int` field in `from_primitives`; `from_primitives` / `to_primitives` round-trip a model with an enum and a `WholeSeconds` field (`{"min_interval_seconds": 3600}` style alias supplied by the test model); `_Id("a") == _Id("a")`, `_Id("a") != _OtherId("a")`, `{_Id("a")}` works, `str(_Id("a")) == "a"`; two entities with the same id and different fields are equal and hash alike; `validate_assignment` rejects a wrong type on an entity; `collect_events()` returns registered events once and `model_dump()` of an aggregate has no events key; `occurred_at.tzinfo is UTC`; `WholeSeconds` rejects `True` and `1.5`, and serializing `timedelta(milliseconds=1500)` raises `ValueError`; `validated_copy` of a model whose `model_validator` rejects the new value raises `ValidationError`; `validation_message` returns `"min_interval: must be positive"`-style one-liners; a third-level subclass of each base raises `TypeError`.
- [ ] **Step 3: Implement the nine modules** to the Interfaces block. `base/model/__init__.py` re-exports all of them.
- [ ] **Step 4: Architecture support.** Add `"base.model.ValueObject"`, `"base.model.EntityId"`, `"base.model.Entity"`, `"base.model.AggregateRoot"`, `"base.model.DomainEvent"` and the same five under `base.` to `runtime-evaluated-base-classes`, so ruff keeps field-annotation imports at runtime. `aggregates.py` treats a subclass of either `AggregateRoot` as an aggregate root; `test_inheritance_depth.py` covers the new bases with the same depth table. Add `test_domain_models_complete.py`: import every module under `context/*/application/domain/model`, and assert every `pydantic.BaseModel` subclass found has `__pydantic_complete__` true; add `test_domain_never_calls_model_copy`, an `ast` scan of the domain for `.model_copy(` calls.
- [ ] **Step 5: Verify** with the four commands. Expected: all pass.
- [ ] **Step 6: Commit** `feat(backend): add pydantic domain base types beside the dataclass ones`.

### Task 3: Maintenance settings on Pydantic, converters retired

**Files:**
- Modify: `context/table_maintenance/application/domain/model/shared/` `maintenance_settings.py`, `rewrite_data_files_settings.py`, `rewrite_manifests_settings.py`, `expire_snapshots_settings.py`, `remove_orphan_files_settings.py` (and any `OperationSettings` alias module)
- Delete: `context/table_maintenance/application/domain/model/shared/invalid_maintenance_settings.py`, `application/service/shared/maintenance_settings_from_dict.py`, `application/service/shared/maintenance_settings_to_dict.py`, `adapter/outbound/shared/sql/maintenance_settings_codec.py`
- Modify callers: `application/service/table/update_table_settings.py`, `table_output_fields.py`, `application/service/table_maintenance_preset/create_table_maintenance_preset.py`, `update_table_maintenance_preset.py`, `table_maintenance_preset_output_fields.py`, `adapter/outbound/table/sql/table_row_mapper.py`, `adapter/outbound/table_maintenance_preset/sql/table_maintenance_preset_row_mapper.py`, the `__init__.py` re-exports, `application/service/shared/translate_domain_errors.py`
- Test: `tests/context/table_maintenance/application/domain/model/shared/test_maintenance_settings_primitives.py` (new), the existing conversion and codec tests (rewritten against `from_primitives` / `to_primitives`, then the converter-specific ones deleted with their modules)

**Interfaces:**
- Consumes: Task 2 `ValueObject`, `WholeSeconds`, `validation_message`.
- Produces: `MaintenanceSettings.from_primitives(data) -> MaintenanceSettings` and `settings.to_primitives() -> dict[str, Any]`, the one wire shape for the API and the settings JSON column; domain field names unchanged (`min_interval: timedelta`), wire names unchanged (`min_interval_seconds`), both accepted when validating. `translate_domain_errors` maps a Pydantic error to `ValidationError(validation_message(exc))`.

- [ ] **Step 1: Capture the golden format before changing anything.** In `test_maintenance_settings_primitives.py`, add `GOLDEN`, the dict today's `MaintenanceSettingsCodec.encode(MaintenanceSettings())` returns, plus `GOLDEN_CUSTOM` for a settings object with every field set to a non-default value (copy both literally from running the current encoder). Tests: `test_defaults_encode_to_golden` (`MaintenanceSettings().to_primitives() == GOLDEN`), `test_custom_round_trips` (`from_primitives(GOLDEN_CUSTOM).to_primitives() == GOLDEN_CUSTOM`), `test_partial_input_takes_defaults` (`from_primitives({"dry_run": True})` equals defaults with `dry_run=True`), and rejections, each raising `ValueError` whose `validation_message` names the field: `{"dry_run": 1}`, `{"rewrite_data_files": {"min_reducible_files": True}}`, `{"unknown": 1}`, `{"rewrite_data_files": {"foo": 1}}`, `{"reconcile_interval_seconds": 0}`, `{"remove_orphan_files": {"older_than_seconds": 3600}}` (below the 1-day floor). Also `test_non_whole_second_duration_fails_to_encode`.
- [ ] **Step 2: Run them.** Expected: FAIL (no `from_primitives` on the dataclasses).
- [ ] **Step 3: Migrate the five settings classes** to `base.model.ValueObject`, constraints as `Field` bounds or `model_validator(mode="after")` (the `__post_init__` bodies), durations as `WholeSeconds` with the `*_seconds` alias; delete `InvalidMaintenanceSettings` and its export.
- [ ] **Step 4: Switch every caller** listed above to `from_primitives` / `to_primitives`, delete the three converter modules and their tests, keep the API-facing tests (they assert 422 and the body); update their expected messages to the `validation_message` one-liners. Positional construction of these classes in `src` and `tests` becomes keyword construction.
- [ ] **Step 5: Verify** with the four commands. Expected: all pass, including the web tests for `PUT /v1/tables/{uuid}/settings` and the preset endpoints.
- [ ] **Step 6: Commit** `refactor(table-maintenance): settings value objects on pydantic, converters retired`.

### Task 4: Remaining table-maintenance shared value objects and domain services

**Files:**
- Modify: every other `ValueObject` in `context/table_maintenance/application/domain/model/shared/` (e.g. `measurement.py`, the planned-operation and observation value objects) and `application/domain/service/` (`table/assess_maintenance.py` and its siblings)
- Test: existing tests under `tests/context/table_maintenance/application/domain/`

**Interfaces:**
- Consumes: Task 2 `ValueObject`, `validated_copy`.
- Produces: no new names; `assess_maintenance` builds changed assessments with `validated_copy`.

- [ ] **Step 1: Write a failing test** in the existing `measurement` test file: `test_threshold_without_comparison_is_rejected` expecting `pydantic.ValidationError` (today `ValueError` from `__post_init__`; the test fails on type until migrated).
- [ ] **Step 2: Migrate** each class: `@dataclass(frozen=True)` → `base.model.ValueObject`, `__post_init__` → `model_validator(mode="after")`, `dataclasses.replace` → `validated_copy`, positional construction → keywords in `src` and `tests`.
- [ ] **Step 3: Adapter round-trip check.** Run the pyiceberg and SQL adapter tests that build these objects (`pytest tests/context/table_maintenance/adapter -q`); fix any adapter that hands a `list` to a `tuple` field or a `str` to an enum field by converting at the adapter, not by loosening strictness.
- [ ] **Step 4: Verify** with the four commands. Expected: all pass.
- [ ] **Step 5: Commit** `refactor(table-maintenance): shared value objects and domain services on pydantic`.

### Task 5: `Table` aggregate

**Files:**
- Modify: `context/table_maintenance/application/domain/model/table/` (all 8 modules: `TableId`, `TableName`, `OperationState`, `Table`, …); `InvalidTableTransition` stays
- Modify: `adapter/outbound/table/sql/table_row_mapper.py` and other constructors of these classes
- Test: existing table domain, service, SQL and web tests

**Interfaces:**
- Consumes: Task 2 `EntityId`, `AggregateRoot`, `ValueObject`, `validated_copy`; Task 3 settings.
- Produces: `Table` and its value objects on `base.model`; `TableId("…")` positional construction unchanged.

- [ ] **Step 1: Write a failing test** `test_table_rejects_wrong_type_on_assignment`: assigning a `str` to a datetime field of a `Table` raises `ValidationError` (fails while `Table` is a dataclass).
- [ ] **Step 2: Migrate** the eight modules (`@dataclass(eq=False)` → `base.model.AggregateRoot[TableId]`, `operation_state.py` `replace` → `validated_copy`), move field-annotation imports out of `TYPE_CHECKING`, convert positional construction.
- [ ] **Step 3: Adapter round-trip check:** `pytest tests/context/table_maintenance/adapter/outbound/table -q` passes; the row mapper reads a stored row into an equal `Table`.
- [ ] **Step 4: Verify** with the four commands. Expected: all pass; `test_domain_models_complete` covers the new classes.
- [ ] **Step 5: Commit** `refactor(table-maintenance): table aggregate on pydantic`.

### Task 6: Preset, discovery settings and discovery rule aggregates

**Files:**
- Modify: `context/table_maintenance/application/domain/model/table_maintenance_preset/`, `table_discovery_settings/`, `table_discovery_rule/` (9 modules)
- Delete: `table_discovery_rule/invalid_table_discovery_rule.py` once its only raises are inside validators; `table_discovery_rule.update` raises `ValidationError` from the same check
- Modify: their SQL row mappers and services
- Test: existing tests for the three aggregates

**Interfaces:**
- Consumes: Task 2 bases, `validation_message`; Task 3 settings.
- Produces: no new names.

- [ ] **Step 1: Write a failing test** `test_include_rule_without_preset_is_rejected` expecting `pydantic.ValidationError` from `TableDiscoveryRule.create(...)`, and `test_update_to_invalid_rule_leaves_rule_unchanged` asserting the rule's fields are unchanged after the failed `update`.
- [ ] **Step 2: Migrate** the nine modules; the shared `_validate` raises a plain `ValueError` (Pydantic wraps it in `ValidationError` inside the validator), and `update` runs the same check before assigning (spec: assignment validation does not cover cross-field rules).
- [ ] **Step 3: Verify** with the four commands; the discovery-rule web tests still answer 422 for an include rule without a preset.
- [ ] **Step 4: Commit** `refactor(table-maintenance): preset and discovery aggregates on pydantic`.

### Task 7: `TableMaintenanceRun` aggregate

**Files:**
- Modify: `context/table_maintenance/application/domain/model/table_maintenance_run/` (7 modules); `InvalidRunTransition` stays
- Modify: its SQL row mapper and services
- Test: existing run tests

**Interfaces:**
- Consumes: Task 2 bases, `validated_copy`.
- Produces: no new names.

- [ ] **Step 1: Write a failing test** `test_forbidden_transition_still_raises_invalid_run_transition` (unchanged behaviour, guards the migration) and `test_operation_update_revalidates`, which makes `validated_copy` the only path by asserting an invalid operation update raises `ValidationError`.
- [ ] **Step 2: Migrate**; the four `replace(...)` calls in `table_maintenance_run.py` become `validated_copy`.
- [ ] **Step 3: Verify** with the four commands; the callback endpoint tests still answer 409 for a forbidden transition.
- [ ] **Step 4: Commit** `refactor(table-maintenance): maintenance run aggregate on pydantic`.

### Task 8: `TableReconciliation` aggregate

**Files:**
- Modify: `context/table_maintenance/application/domain/model/table_reconciliation/` (7 modules)
- Delete: `invalid_reconciliation.py` once its raises are validator checks
- Modify: its SQL row mapper and the record and list services
- Test: existing reconciliation tests

**Interfaces:**
- Consumes: Task 2 bases.
- Produces: no new names.

- [ ] **Step 1: Write a failing test** for each check that raised `InvalidReconciliation`, now expecting `pydantic.ValidationError`.
- [ ] **Step 2: Migrate**, delete `InvalidReconciliation`.
- [ ] **Step 3: Verify** with the four commands; `GET /v1/tables/{uuid}/reconciliations` web tests return the same JSON.
- [ ] **Step 4: Commit** `refactor(table-maintenance): reconciliation aggregate on pydantic`.

### Task 9: Catalog aggregate and shared catalog value objects

**Files:**
- Modify: `context/catalog/application/domain/model/catalog/` (9 modules) and `model/shared/` (3 modules)
- Delete: `context/catalog/application/service/catalog/connection_config_from_dict.py`, `connection_config_to_dict.py`, `storage_config_from_dict.py`, `storage_config_to_dict.py`
- Modify: `create_catalog.py`, `update_catalog.py`, `catalog_output_fields.py`, `service/catalog/__init__.py`, the Polaris catalog mapper
- Test: existing catalog tests; new `tests/context/catalog/application/domain/model/catalog/test_catalog_config_primitives.py`

**Interfaces:**
- Consumes: Task 2 `ValueObject`, `from_primitives`, `to_primitives`, `validation_message`.
- Produces: `ConnectionConfig.from_primitives` / `to_primitives` and `StorageConfig.from_primitives` / `to_primitives` replacing the four converters, with today's dict shapes.

- [ ] **Step 1: Capture golden dicts** from the four current converters (one per storage type and authentication type) into `test_catalog_config_primitives.py`, with round-trip and rejection tests in the Task 3 style. The secret-redaction behaviour of `connection_config_to_dict` (fields it leaves out) is pinned by a test that the described dict has no secret keys.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Migrate** the catalog and shared modules, switch callers, delete the converters; catalog services that catch `ValueError` report `validation_message(exc)`.
- [ ] **Step 4: Verify** with the four commands; catalog web tests return the same bodies.
- [ ] **Step 5: Commit** `refactor(catalog): catalog aggregate on pydantic, config converters retired`.

### Task 10: Remaining catalog aggregates

**Files:**
- Modify: `context/catalog/application/domain/model/namespace/`, `generic_table/`, `view/`, `table/` (17 modules) and their Polaris mappers
- Test: existing catalog tests; `test_generic_table_services.py:48` and `test_view_services.py:77` compare with `asdict`, switch to `==` on the outputs

**Interfaces:**
- Consumes: Task 2 bases.
- Produces: no new names.

- [ ] **Step 1: Write a failing test** `test_view_version_requires_keywords` asserting `ViewVersion(...)` positional construction raises `TypeError` once migrated, then convert every positional value-object call in these four packages and their tests to keywords (a scripted rewrite is fine; review the diff).
- [ ] **Step 2: Migrate** the four aggregates and their value objects.
- [ ] **Step 3: Verify** with the four commands.
- [ ] **Step 4: Commit** `refactor(catalog): namespace, table, view and generic table on pydantic`.

### Task 11: Retire the dataclass bases

**Files:**
- Delete: `base/value_object.py`, `base/entity_id.py`, `base/entity.py`, `base/aggregate_root.py`, `base/domain_event.py` and their tests under `tests/base/`
- Move: `base/model/*.py` → `base/`, `tests/base/model/*` → `tests/base/`; delete `base/model/`
- Modify: every `from base.model import` → `from base import`; `base/__init__.py`; `pyproject.toml` (drop the `base.model.*` entries); `aggregates.py`, `test_inheritance_depth.py` (one family again); `src/data-platform/backend/CLAUDE.md` (DDD base types section, examples without `@dataclass`); `docs/agents/project-history.md`
- Test: whole suite

**Interfaces:**
- Consumes: Tasks 2–10 (no domain class left on a dataclass base).
- Produces: `from base import ValueObject, EntityId, Entity, AggregateRoot, DomainEvent, WholeSeconds, validated_copy, validation_message`.

- [ ] **Step 1: Prove nothing uses the old bases:** `grep -rn "@dataclass" context/*/application/domain base` returns nothing. If it returns anything, migrate it first.
- [ ] **Step 2: Delete, move and rewrite imports** as listed.
- [ ] **Step 3: Verify** with the four commands, then `task gates:pre-pr`. Expected: all pass.
- [ ] **Step 4: Deploy check** on minikube (`KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`): an existing table's settings page loads, saving settings round-trips, Reconcile now records a reconciliation.
- [ ] **Step 5: Commit** `refactor(backend): domain model fully on pydantic`, and add the project-history line.
