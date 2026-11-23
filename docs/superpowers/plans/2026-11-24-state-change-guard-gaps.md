# State-Change Guard Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every known gap in KCL-100's rule "an aggregate changes only through its own methods": no bypass the scan misses, no collection outside code can edit in place, no layer left unscanned, and no false alarm on a class calling its own private helper.

**Architecture:** Two complementary guards, no runtime frame check. **Structure:** every list, dict or set field of a domain model (entity, value object, domain event) becomes immutable (`tuple`, `frozenset`, or a new `base.ReadOnlyMapping`), so outside code has nothing it can edit in place, and an architecture test refuses any mutable collection type in a domain model field. **Scan:** `tests/architecture/test_state_changes_through_methods.py` learns the reflective bypasses, narrows its `.state` exemption to Starlette's `app.state`, allows a class's calls to its own private helpers, and scans every file of every context instead of only services and adapters.

**Tech Stack:** Python 3.14, Pydantic v2 (strict models), pytest, `ast`, mutmut.

**Spec:** Linear KCL-100 (reopened 2026-11-24) and the decisions the user made on 2026-11-24, recorded here: (1) the scan flags `setattr`/`delattr`/`object.__setattr__`/`__dict__`-style writes and allows only `app.state`; (2) aggregate collection fields become immutable types so outside code cannot mutate them; (3) the scan covers domain services and every aggregate (an aggregate changes only itself); (4) a class may call its own private static helpers (`Schema._walk`); (5) attribute writes on locally built plain objects stay flagged (build them in one call); no runtime check of who calls `__setattr__`; TDD; verify by redeploying the backend and a light smoke check, no cluster rebuild.

## Global Constraints

- Backend rules in `src/data-platform/backend/CLAUDE.md` and the root `CLAUDE.md` apply: one object per file, `from __future__ import annotations`, ABC over Protocol, `uv run`, never `cd`, no compatibility code (the cluster keeps its data across a redeploy only because nothing stored changes shape: the JSON a read-only mapping or tuple serializes to is the same as before).
- No runtime frame inspection in `Entity.__setattr__` (user, 2026-11-24).
- Every commit passes `pytest -v`, `ty check`, `ruff check .`, `ruff format --check .`, `lint-imports`.
- Rule-heavy code gets a mutation step: mutmut over `base.read_only_mapping*`; 4+ hand mutants on the scan's checkers (the scan lives in `tests/`, which mutmut does not mutate).
- Commit messages: conventional, lower-case subject, end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. Do not push without asking.

## Review Focus

1. An aggregate rebuilt from a JSON column or a Polaris response, where a collection arrives as a JSON array or object, must still load: strict Pydantic refuses a `list` for a `tuple` field in Python mode — Task 2 runs every SQL and Polaris repo test, and Step 2.4 names the converters.
2. A use-case output, a SQL row or a Temporal payload built from one of these fields (`run.metrics`, `run.procedure_args`, `reconciliation.wake_reasons`, `table.properties`) must still be plain JSON — Task 1 pins `model_dump`/`model_dump_json` to plain `dict`/`list`, and Task 2 adds `test_run_output_fields_hand_out_plain_dicts`.
3. A test fake or test that deep-copies an aggregate (`model_copy(deep=True)` in the in-memory repos) must keep working — `ReadOnlyMapping` supports `copy`/`deepcopy`/pickle, Task 1 pins it.
4. Equality and hashing: an entity or value object holding a `ReadOnlyMapping` equals one built from the same `dict`, and a value object stays hashable when its values are — Task 1 pins both.
5. The scan must not newly flag the domain's legal code once it covers every layer: `Schema._walk(…)` inside `Schema`, `TableMaintenanceRun._clamp(…)` inside `TableMaintenanceRun`, `type(self)._x()`, `super().__setattr__(…)` — Task 3's allowed cases and the real scan.

---

### Task 1: `base.ReadOnlyMapping`

**Files:**
- Create: `src/data-platform/backend/base/read_only_mapping.py`
- Modify: `src/data-platform/backend/base/__init__.py` (export `ReadOnlyMapping`)
- Test: `src/data-platform/backend/tests/base/test_read_only_mapping.py`

**Interfaces:**
- Produces: `class ReadOnlyMapping[K, V](collections.abc.Mapping[K, V])` — built from any mapping (`ReadOnlyMapping({"a": 1})`); usable as a Pydantic field annotation `ReadOnlyMapping[str, int]`; values that are `dict`/`list` (also nested, for `Any`-valued mappings) are frozen to `ReadOnlyMapping`/`tuple`; `model_dump()` and `model_dump_json()` give plain `dict`/`list` (nested too); hashable when its values are; supports `copy.copy`, `copy.deepcopy`, `pickle`; `__eq__` against any `Mapping` compares items; `__repr__` is `ReadOnlyMapping({...})`.

- [ ] **Step 1: Write the failing tests** in `tests/base/test_read_only_mapping.py`, against a strict stub model `class _Holder(ValueObject): counts: ReadOnlyMapping[str, int]` and `class _Bag(ValueObject): data: ReadOnlyMapping[str, Any]` (a `ValueObject` is strict and frozen; add one `Entity` stub `class _Box(Entity[_BoxId]): counts: ReadOnlyMapping[str, int]` for reassignment):
  - `test_a_field_accepts_a_dict_and_holds_a_read_only_mapping` — `type(_Holder(counts={"a": 1}).counts) is ReadOnlyMapping`.
  - `test_item_assignment_and_deletion_are_refused` — `h.counts["a"] = 2` and `del h.counts["a"]` raise `TypeError`; `h.counts` has no `update`, `pop`, `clear`, `setdefault` (`not hasattr`).
  - `test_keys_and_values_are_validated_strictly` — `_Holder(counts={"a": "1"})` and `_Holder(counts={1: 1})` raise `InvariantViolation`.
  - `test_a_read_only_mapping_is_accepted_as_is` — `_Holder(counts=ReadOnlyMapping({"a": 1})).counts == {"a": 1}`.
  - `test_reassigning_the_field_holds_a_read_only_mapping_again` — `box.counts = {"b": 2}` then `type(box.counts) is ReadOnlyMapping`.
  - `test_nested_dicts_and_lists_are_frozen` — `_Bag(data={"x": {"y": [1, {"z": 2}]}})`: `data["x"]["y"] == (1, ReadOnlyMapping({"z": 2}))`, `data["x"]["k"] = 1` raises `TypeError`.
  - `test_dumps_give_plain_dicts_and_lists` — `_Bag(...).model_dump() == {"data": {"x": {"y": [1, {"z": 2}]}}}` with `type(...["data"]) is dict` and the inner list a `list`; `model_dump_json()` equals `'{"data":{"x":{"y":[1,{"z":2}]}}}'`; `_Bag.model_validate_json(that)` round-trips equal.
  - `test_equality_with_a_dict_and_between_models` — `ReadOnlyMapping({"a": 1}) == {"a": 1}`, `!= {"a": 2}`, and `_Holder(counts={"a": 1}) == _Holder(counts=ReadOnlyMapping({"a": 1}))`.
  - `test_hashable_when_its_values_are` — `hash(ReadOnlyMapping({"a": 1})) == hash(ReadOnlyMapping({"a": 1}))`; `hash(_Holder(counts={"a": 1}))` works.
  - `test_copy_deepcopy_and_pickle_keep_it_read_only` — for each of `copy.copy`, `copy.deepcopy`, `pickle.loads(pickle.dumps(...))`: result `== {"a": 1}` and `type(...) is ReadOnlyMapping`; `box.model_copy(deep=True).counts == {"a": 1}`.
  - `test_repr_names_the_type` — `repr(ReadOnlyMapping({"a": 1})) == "ReadOnlyMapping({'a': 1})"`.
- [ ] **Step 2: Run** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/base/test_read_only_mapping.py -v`. Expected: FAIL at import (`cannot import name 'ReadOnlyMapping'`).
- [ ] **Step 3: Implement** `ReadOnlyMapping` in `base/read_only_mapping.py`: it stores a private `dict` of frozen values; `__getitem__`, `__iter__`, `__len__`, `__eq__` (with any `Mapping`), `__hash__` (`hash(frozenset(self.items()))`), `__repr__`, and `__reduce__` returning `(ReadOnlyMapping, (dict(self),))` for copying and pickling. `__get_pydantic_core_schema__(cls, source, handler)` reads `K`, `V` from `typing.get_args(source)` (default `Any`, `Any`) and builds a union of an `is_instance_schema(ReadOnlyMapping)` (then re-validated through the dict schema) and `handler.generate_schema(dict[K, V])`, each followed by a `no_info_after_validator_function` that wraps the result; serialization is a `plain_serializer_function_ser_schema` that thaws recursively to `dict`/`list`. Private helpers `_frozen(value)` / `_thawed(value)` in the same file.
- [ ] **Step 4: Run** the new tests, then `tests/base`. Expected: PASS.
- [ ] **Step 5: Mutation step:** `task -d src/data-platform/backend mutation-test MUTANTS='base.read_only_mapping*'` (after `rm -f src/data-platform/backend/mutants/mutmut-stats.json`); kill each survivor with a test or ledger why it is equivalent.
- [ ] **Step 6: Commit** `feat(base): a read-only mapping for domain model fields (KCL-100)`.

### Task 2: Domain model collections are immutable

**Files:**
- Create: `src/data-platform/backend/tests/architecture/test_domain_collections_are_immutable.py`
- Modify (field types; the list is what a scan of every `Entity`/`ValueObject`/`DomainEvent` subclass found on 2026-11-24):
  - catalog: `domain/model/catalog/catalog.py` `properties`; `generic_table/generic_table.py` `properties`; `namespace/namespace.py` `properties`; `table/snapshot.py` `summary`; `table/table.py` `snapshots`, `properties`; `table/table_property_reset.py` `updates`; `view/view.py` `versions`, `properties`.
  - table maintenance: `domain/model/table/table.py` `operation_states`; `shared/table_observation.py` `properties`; `table_maintenance_run/table_maintenance_run.py` `procedure_args`, `metrics`; `table_reconciliation/table_reconciliation.py` `wake_reasons`.
  - Every consumer the suite shows breaking: an adapter that builds one of these models from a JSON array (convert to `tuple(...)`), and a strict output, row or payload field that receives one (copy with `dict(...)`/`list(...)`, or let `model_dump` thaw it).
  - Tests that edit these collections in place (found 2026-11-24): `test_assess_maintenance.py` (11), `test_assessment_plan.py` (6), `test_tables_polaris_repo.py` (2), `test_tables_sql_repo.py` (2), and one each in catalog `test_table_services.py`, `test_plan_table_maintenance_service.py`, `test_table_observation_from_gateway.py`, table-maintenance `test_table_services.py`, `fakes/in_memory_table_discovery_policies_repo.py`, `fakes/in_memory_table_maintenance_policies_repo.py`. Each builds the model with the collection it needs, or calls the aggregate's method, instead of editing the collection.
- Docs: `src/data-platform/backend/CLAUDE.md` (DDD Base Types: a `ReadOnlyMapping` line; the "changes only through its own methods" rule bullet: collections are immutable), `docs/adr/0009-pydantic-in-the-domain-model.md` (one Consequences bullet).

**Interfaces:**
- Consumes: `ReadOnlyMapping` (Task 1).
- Produces: every listed field typed `tuple[X, ...]`, `frozenset[X]` or `ReadOnlyMapping[K, V]`; `mutable_collection_fields(cls: type[BaseModel]) -> list[str]` in the new test module (names `"<field>: <annotation>"`).

- [ ] **Step 1: Write the failing tests** in `test_domain_collections_are_immutable.py`:
  - `_domain_models()` walks each context's `application.domain.model` package (as `test_entity_ids_are_fixed.py` does) and collects every subclass of `Entity`, `ValueObject` or `DomainEvent` defined there.
  - `mutable_collection_fields(cls)` returns the fields whose annotation contains `list`, `dict`, `set`, `collections.abc.MutableMapping`, `MutableSequence` or `MutableSet` anywhere (inside `X | None`, `tuple[list[int], ...]`, `ReadOnlyMapping[str, list[int]]` too: walk `typing.get_args` recursively).
  - `test_the_scan_finds_models_of_every_context` — every context contributes models.
  - `test_domain_model_collections_are_immutable[<Class>]` — `assert mutable_collection_fields(cls) == []`, parametrized over `_domain_models()`.
  - Self-checks with stub models: `list[int]`, `dict[str, int] | None`, `tuple[list[int], ...]`, `ReadOnlyMapping[str, list[int]]`, `set[str]` are each flagged; `tuple[int, ...]`, `frozenset[str]`, `ReadOnlyMapping[str, int]`, `str`, `int | None` are not.
  - In `tests/context/table_maintenance/application/service/table_maintenance_run/`: `test_run_output_fields_hand_out_plain_dicts` — the output fields of a run with `metrics={"files": 3}` and `procedure_args={"a": {"b": 1}}` hold `dict` instances (not `ReadOnlyMapping`), equal to the inputs.
- [ ] **Step 2: Run** the new architecture test. Expected: FAIL for the 11 classes listed above (and no others); the self-checks fail only where they need `mutable_collection_fields`.
- [ ] **Step 3: Change the field types**, then run the whole backend suite and fix every consumer and test it shows (Files list). Converters: a repo that loads a list from JSON passes `tuple(...)`; a model loaded with `model_validate_json` needs no change (JSON arrays validate into tuples). No `.get(...)` or `or ()` defaults on the way in (no compatibility code).
- [ ] **Step 4: Run** the full suite and all checks. Expected: PASS; `test_domain_collections_are_immutable` green for every model.
- [ ] **Step 5: Hand mutants** on `mutable_collection_fields` (in a scratch copy, as for KCL-100's scan): stop recursing into `get_args`; drop `dict`; drop `set`; treat `ReadOnlyMapping[str, list[int]]` as fine. Each must fail a self-check.
- [ ] **Step 6: Docs**, then **Commit** `refactor(domain): domain model collections cannot be edited in place (KCL-100)`.

### Task 3: The scan catches reflective bypasses and covers every layer

**Files:**
- Modify: `src/data-platform/backend/tests/architecture/test_state_changes_through_methods.py`
- Modify: `src/data-platform/backend/CLAUDE.md` (the rule bullet: what is flagged, `app.state` only, every layer, build plain objects in one call)

**Interfaces:**
- Produces: `foreign_assignments(source: str) -> list[str]`, `foreign_private_calls(source: str) -> list[str]` (unchanged signatures) and a new `reflective_writes(source: str) -> list[str]`, each returning `"<line>: <code>"`.

- [ ] **Step 1: Write the failing tests** (parametrized self-checks, like the existing ones):
  - `test_the_reflective_check_flags_bypasses` over: `setattr(table, "status", x)`, `delattr(table, "status")`, `object.__setattr__(table, "status", x)`, `object.__delattr__(table, "status")`, `table.__setattr__("status", x)`, `table.__dict__["status"] = x`, `table.__dict__.update(status=x)`, `vars(table)["status"] = x`, `table.model_copy(update={"status": x})`, `Table.model_construct(status=x)` — each `reflective_writes(src)` is non-empty.
  - `test_the_reflective_check_allows_own_and_plain_calls` over: `setattr(self, "x", 1)`, `self.__dict__.update(x=1)`, `super().__setattr__(name, value)`, `table.model_copy()`, `getattr(table, "status")`, `vars()` — each `== []`.
  - `test_the_assignment_check_allows_only_starlettes_app_state` — `app.state.x = 1` and `request.app.state.x = 1` → `[]`; `table.state.status = x` and `run.state.flag = 1` → flagged.
  - `test_a_class_may_call_its_own_private_helpers` — `foreign_private_calls` of `"class Schema:\n    def f(self):\n        return Schema._walk(1)\n"` and of `"class Run:\n    def f(self):\n        return type(self)._clamp(1)\n"` is `[]`.
  - `test_another_class_or_module_code_calling_a_private_helper_is_flagged` — `"class Other:\n    def f(self):\n        return Schema._walk(1)\n"` and module-level `"Schema._walk(1)\n"` are flagged.
  - `test_an_attribute_write_on_a_locally_built_object_is_flagged` — `"def f():\n    b = Builder()\n    b.x = 1\n"` is flagged (decision 5).
  - `test_services_and_adapters_…` tests become `test_context_code_…` and parametrize over every `.py` file under each context (domain model, domain service, port, service, adapter); a third per-file test `test_context_code_makes_no_reflective_write`; `test_the_scan_covers_every_layer_of_every_context` asserts files from `application/domain/model`, `application/domain/service`, `application/port`, `application/service` and `adapter` of each context.
- [ ] **Step 2: Run** the module. Expected: the new self-checks fail; with the wider scope, the per-file tests fail exactly on `context/catalog/application/domain/model/shared/schema.py` (`Schema._walk`, lines 22 and 30) and `context/table_maintenance/application/domain/model/table_maintenance_run/table_maintenance_run.py` (`TableMaintenanceRun._clamp`, line 401).
- [ ] **Step 3: Implement.** `reflective_writes` flags: a call to `setattr`/`delattr` whose first argument is not `self`/`cls`; any call of `__setattr__`/`__delattr__` on a receiver other than `self`, `cls` or `super()` (so `object.__setattr__(…)` is flagged); any `.__dict__` on a receiver other than `self`/`cls`; `vars(<arg>)` with an argument other than `self`/`cls`; `.model_copy(...)` with an `update=` keyword; any `.model_construct(...)`. In `_is_foreign`, the `state` exemption applies only when the owner is `app.state` (`Name("app")` or an attribute named `app`). `foreign_private_calls` walks with the stack of enclosing class names and allows a receiver that is `Name(<an enclosing class>)` or `type(self)`/`type(cls)`.
- [ ] **Step 4: Run** the module, then the full suite and checks. Expected: PASS, with no violation in any context file (production code had none of the bypasses on 2026-11-24).
- [ ] **Step 5: Hand mutants** (scratch copy): allow `setattr` on any object; drop the `model_copy(update=)` case; exempt any `.state`; allow any class name as a receiver of a private call; scan only services and adapters again. Each must fail a test. Ledger killed/survived.
- [ ] **Step 6: Docs**, then **Commit** `test(architecture): the state-change scan catches reflective writes in every layer (KCL-100)`.

### Task 4: Redeploy, smoke check, close out

- [ ] **Step 1:** `task gates:pre-pr` from the repo root. Expected: exit 0.
- [ ] **Step 2: Redeploy the backend** (no rebuild): `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh` then `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/validate.sh`. Expected: both exit 0, the api, worker and event-consumer pods run the new image tag.
- [ ] **Step 3: Smoke check** against the table `iceberg.kcl110.orders` left by the 2026-11-23 check (uuid `4504b45d-bea7-4a04-a5a3-08d369e83441`): `GET /v1/tables/{uuid}` answers 200 with its operation states; one manual `rewrite_manifests` run ends `succeeded` with a size on every attempt; the catalog context's table and namespace endpoints answer 200 with `properties` (and the table's snapshots); a reconciliation record lists its wake reasons; worker, api and event-consumer logs since the redeploy have no `TypeError`, `ValidationError`, `KeyError` or `Traceback`. Write the result to `/Users/kcl/.claude/jobs/ffac9ee8/tmp/kcl100-gaps-smoke.md`.
- [ ] **Step 4: Linear:** a dated Traditional Chinese comment on KCL-100 (what was missing, what changed, commits, the smoke result), move it back to Done; `docs/agents/project-history.md` gains a 2026-11-24 line. Commit the history line with Task 3's docs if not yet committed, else `docs(agents): record the state-change guard gaps closed (KCL-100)`.
- [ ] **Step 5:** ask the user before pushing.
