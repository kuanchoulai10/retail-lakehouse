# Maintenance policies and discovery rules

Status: draft, 2026-11-11. Replaces presets, per-table settings and the discovery switch with two separate ideas: discovery rules decide which tables are managed, and maintenance policies, attached to a catalog, a namespace or a table, decide how a managed table is maintained.

## Why

**Discovery does two jobs today.** One discovery pass lists the tables of a catalog, decides by the discovery rules whether each new table is managed, and copies the matched rule's preset settings onto the table. Once copied, the settings belong to the table: editing the preset changes nothing for tables already registered, and a table, once decided, is never decided again. Pause, resume, manual include and manual exclude add a second, per-table way of deciding what is managed.

**The settings themselves mix two kinds of values.** For every operation, `MaintenanceSettings` holds when the operation is due (`min_reducible_files`, `min_interval`) next to how it runs (`target_file_size_bytes`, `scope`). Some of how it runs is not in the settings at all: `min-input-files` and `partial-progress.enabled` are hard-coded in `maintenance_procedure_args`.

The user wants each concept to do one thing:

- **Discovery rules** answer only "which tables are managed", and they are re-applied on every discovery pass, so the managed set always matches the rules.
- **A maintenance policy** answers "how is a managed table maintained". It is attached to a catalog, a namespace or a table and inherited downward, in the style of Apache Polaris policies, and it takes effect immediately on every table it applies to.
- Inside a policy, each operation separates its **trigger policy** (when it is due) from its **execution policy** (the values handed to the Iceberg procedure).

## Relation to earlier specs

The reconciliation redesign (`2026-11-10-reconciliation-records-design.md`) listed four specs. Spec 1 (reconciliation records and dry run) has landed. **This spec replaces spec 2** ("per-operation conditions combinable with AND or OR, compaction skips recently written partitions"): the user dropped AND/OR combinations in favour of OR only, and dropped partition selection by last-updated time. Specs 3 (reconciliation triggers) and 4 (one workflow per operation) are unaffected and stay deferred. "Policy inheritance", deferred there, is delivered here.

## Goals

- Discovery rules decide alone which tables are managed. Saving a rule change applies it at once.
- The console shows the discovery rules as an ordered, editable list, with a preview of which tables each rule would manage.
- A managed table always resolves exactly one maintenance policy: the one attached nearest to it, or the platform default.
- Editing or re-attaching a policy changes the maintenance of every table it applies to, from that table's next reconciliation.
- Every reconciliation record names the policy and version it used, and where that policy was attached.
- Each operation's trigger and execution values are visibly separate, in the model, the API and the console.

## Non-goals

- No data migration. The platform is in development; the cluster is rebuilt with the new schema. Existing presets, rule-to-preset links and per-table settings are dropped, not converted.
- No change to when a table is reconciled (the reconcile loop, its timer, catalog-commit wakes) beyond what policies feed it. That is spec 3.
- No change to how a maintenance run executes its operations. That is spec 4.
- No storing of maintenance policies in Polaris. Polaris is the model for the API and the inheritance rules, not the store.
- No new compaction strategies (sort, z-order) or new Iceberg procedure options beyond those listed below.

## Anti-goals

- **No second way to decide what is managed.** Pause, resume, manual include, manual exclude and "reset selection" go away. If a table should not be managed, a rule says so.
- **No merging of policies.** A policy found lower in the hierarchy replaces the higher one whole; fields are never combined across levels. A user must be able to read one policy and know everything that applies.
- **No "selection" of partitions by write time, quiet periods or predicates.** Rejected as complexity without a concrete need.
- **"Policy" means maintenance policy only.** Discovery is "discovery rules", never "discovery policy".

## Vocabulary

- **Discovery rule**: one include or exclude rule. **Discovery rules**: the ordered list of them. The verb is *discover*, the object is *tables*: "discover tables".
- **Managed table**: a table the discovery rules include. It has a reconciliation workflow and is maintained.
- **Maintenance policy** (UI: "Policy" where unambiguous): a named, versioned description of how managed tables are maintained.
- **Attachment** (Polaris: policy mapping): a maintenance policy bound to one **target**, which is a catalog, a namespace or a table.
- **Applicable policy**: the policy that applies to a table after inheritance.
- **Trigger policy**: within one operation, the cooldown and the conditions that make the operation due.
- **Execution policy**: within one operation, the values passed to the Iceberg procedure.
- **Cooldown**: the minimum time after an operation last ran before it may run again (today's `min_interval`).

## Discovery rules

### The rule

| Field | Meaning |
|---|---|
| `id` | Generated. |
| `priority` | Integer, unique across rules. Lower is applied first. |
| `action` | `include` or `exclude`. |
| `enabled` | A disabled rule is skipped as if absent. |
| `catalogs` | Non-empty list of globs on the catalog name. |
| `namespaces` | Non-empty list of globs on the full dotted namespace name (`prod.*` matches `prod.sales`). |
| `tables` | Non-empty list of globs on the table name. |
| `created_at`, `updated_at` | Timestamps. |

A rule matches a table when **any** glob of each field matches and **all three** fields match. Matching is case-sensitive, as today (`fnmatch.fnmatchcase`). A table is managed when the first enabled matching rule, in priority order, is `include`; an `exclude` match or no match leaves it unmanaged.

```json
{
  "id": "b7d1…",
  "priority": 10,
  "action": "exclude",
  "enabled": true,
  "catalogs": ["*"],
  "namespaces": ["production_*"],
  "tables": ["tmp_*", "staging_*"]
}
```

### The aggregate

**`TableDiscoveryRules`, one per platform, holds the rules as entities.** First-match evaluation and unique priorities are properties of the whole ordered list, so the list is the consistency boundary, and **it is written whole**: the console edits a draft of the full list (the same list the preview takes) and saves it in one `PUT /discovery-rules` carrying the list's `version`; a stale version answers 409. Unique priorities are checked on that whole list, so reordering never passes through an invalid state, and one save starts one discovery round. Compared with today: the rule field `effect` becomes `action`, each field holds a list of globs instead of one (`TablePattern`), and priorities become unique instead of tie-broken by rule id. The singleton `TableDiscoverySettings` aggregate and its on/off switch are deleted: with rules re-applied on every pass, switching discovery off would mean unmanaging everything, which a rule can say more plainly. The discovery schedule therefore always runs.

### Discovering tables

A discovery pass (`TableDiscoveryWorkflow`, per covered catalog, on its schedule) lists the catalog's tables and, for every table:

1. Evaluates the rules.
2. If the table is managed and not yet known, registers it as managed and signal-with-starts its reconciliation workflow.
3. If it is known and managed, renames it if its name changed, and signal-with-starts its reconciliation workflow (today's "ensure enrolled", so a lost workflow comes back).
4. If it is known, managed before, and now unmanaged, marks it unmanaged and sends its reconciliation workflow the stop signal.
5. If it is unmanaged before and managed now, marks it managed and signal-with-starts its workflow under the same workflow ID.

A catalog-wide pass also marks known tables that are no longer in the catalog as dropped, as today; a namespace-scoped pass never does. Catalog events from Polaris (`process_table_hint`) apply the same per-table steps to the one table or namespace they name.

**Saving a rule change discovers tables at once.** After a save of the rule list commits, the API starts one discovery run per covered catalog (the existing workflow, outside its schedule). It does not wait for them. Overlapping runs are already safe: each table's changes are idempotent.

### Leaving management

When a table becomes unmanaged, a maintenance run already in flight always runs to completion. The reconciliation workflow plans nothing more and ends once that run reports back; this is today's stop behaviour. If a later rule change manages the table again, discovery starts its workflow again with the same workflow ID. The table row is kept with status `unmanaged`, so its reconciliation records, its maintenance runs and its per-operation last-run state survive.

### Preview

`POST /discovery-rules/preview` takes a full candidate list of rules, unsaved, and returns every table of every covered catalog with the rule that would decide it (or none) and whether it would be managed, plus counts. The console calls it as the user edits, so a mistake shows before it is saved. The preview reads the catalog through the existing catalog gateway and writes nothing.

## Maintenance policies

### Content

```json
{
  "name": "default",
  "description": "Platform default",
  "version": 3,
  "reconcile_interval_seconds": 3600,
  "dry_run": false,
  "operations": {
    "rewrite_data_files": {
      "enabled": true,
      "scope": { "unit": "partition" },
      "trigger_policy": {
        "cooldown_seconds": 3600,
        "conditions": {
          "reducible_files": { "at_least": 5 }
        }
      },
      "execution_policy": {
        "target_file_size_bytes": null,
        "min_input_files": 2,
        "partial_progress": { "enabled": true }
      }
    },
    "rewrite_manifests": {
      "enabled": true,
      "trigger_policy": {
        "cooldown_seconds": 21600,
        "conditions": {
          "small_manifests": { "at_least": 5, "smaller_than_bytes": null }
        }
      },
      "execution_policy": {}
    },
    "expire_snapshots": {
      "enabled": true,
      "trigger_policy": {
        "cooldown_seconds": 21600,
        "conditions": {
          "expirable_snapshots": { "at_least": 1 }
        }
      },
      "execution_policy": { "older_than_seconds": 86400, "retain_last": 10 }
    },
    "remove_orphan_files": {
      "enabled": true,
      "trigger_policy": { "cooldown_seconds": 604800, "conditions": {} },
      "execution_policy": { "older_than_seconds": 259200 }
    }
  },
  "created_at": "…",
  "updated_at": "…"
}
```

The values shown are the platform default policy's content, equal to today's `MaintenanceSettings()` defaults plus the two values hard-coded in `maintenance_procedure_args`.

A write carries `description`, `reconcile_interval_seconds`, `dry_run` and all four `operations`, always whole; `description` may be empty. `version`, `created_at` and `updated_at` are set by the server. An update also carries the `version` the caller read and answers 409 if the policy has moved on, as Polaris's update-policy does.

### The model

```python
class AtLeast(ValueObject):
    at_least: PositiveInt

class SmallManifests(AtLeast):
    smaller_than_bytes: PositiveInt | None = None

class Conditions(ValueObject):
    """Every field optional; a missing field is not checked; fields combine with OR."""

class RewriteDataFilesConditions(Conditions):
    reducible_files: AtLeast | None = None

class RewriteManifestsConditions(Conditions):
    small_manifests: SmallManifests | None = None

class ExpireSnapshotsConditions(Conditions):
    expirable_snapshots: AtLeast | None = None

class RemoveOrphanFilesConditions(Conditions): ...

class TriggerPolicy[C: Conditions](ValueObject):
    cooldown: WholeSeconds  # alias cooldown_seconds
    conditions: C

class ExecutionPolicy(ValueObject): ...

class RewriteDataFilesTriggerPolicy(TriggerPolicy[RewriteDataFilesConditions]): ...
class RewriteDataFilesExecutionPolicy(ExecutionPolicy):
    target_file_size_bytes: PositiveInt | None = None
    min_input_files: PositiveInt
    partial_progress: PartialProgress

class OperationPolicy[T: TriggerPolicy, E: ExecutionPolicy](ValueObject):
    enabled: bool
    trigger_policy: T
    execution_policy: E

class RewriteDataFilesPolicy(OperationPolicy[RewriteDataFilesTriggerPolicy, RewriteDataFilesExecutionPolicy]):
    scope: CompactionScope  # serialised as {"unit": "partition" | "table"}
```

and likewise for the other three operations. `TableMaintenancePolicy` is the aggregate root: `name` (its identity), `description`, `version`, `reconcile_interval`, `dry_run`, `operations` (a value object with one field per operation), timestamps. All of these follow the existing base types (`ValueObject` frozen, strict, `extra="forbid"`; wire input through `from_primitives`).

**`scope` sits on the operation, not inside either policy,** because both use it: the trigger policy measures per partition or across the table, and the execution policy compacts the qualifying partitions or the whole table. Only `rewrite_data_files` has a scope; the other operations act on the whole table.

### Triggering

An operation is **due** when it is enabled, its cooldown has passed since it last ran, and **either** its conditions are empty **or any** of its conditions holds. Today's failure backoff on the cooldown stays.

| Condition | Measured |
|---|---|
| `reducible_files.at_least` | Files that compaction would remove, as computed today by `compute_reducible_files`. With `scope.unit` `partition`, measured per partition and the operation is due if any partition qualifies; with `table`, summed across the table. |
| `small_manifests.at_least` | Manifests smaller than `smaller_than_bytes`, or than today's derived default when it is null. |
| `expirable_snapshots.at_least` | Snapshots older than the execution policy's `older_than` and outside its `retain_last`, as `_assess_snapshots` counts today. This is the one condition that reads execution values, because "expirable" is defined by them; with `at_least: 1` it reproduces today's behaviour. |

**Conditions do not read the execution policy** (except `expirable_snapshots`, above). `reducible_files` is measured against the table's own `write.target-file-size-bytes` property, or 512 MiB when the table has none, even when the execution policy sets `target_file_size_bytes`. The user accepted that the two can then disagree and will revisit it.

The reconciliation record's measurements (`Measurement`, `OperationAssessment`) keep their shape. `ConditionCombine` is removed: the combination is always OR.

### Executing

`maintenance_procedure_args` reads the execution policy instead of constants. For `rewrite_data_files`: `target-file-size-bytes` is the execution policy's value, else the table property, else 512 MiB; `min-input-files` and `partial-progress.enabled` come from the execution policy. The other operations map as today. The Spark job request (`GLAC_REQUEST`) keeps its shape.

### Invariants of a policy

- `name` is unique, matches `^[A-Za-z0-9_-]{1,64}$`, and never changes.
- Every successful update increments `version` by one.
- A policy with any attachment cannot be deleted.
- The platform default policy, named `default`, always exists (there are no migrations: the schema comes from `metadata.create_all` in `adapter/outbound/shared/sql/create_schema.py`, so a startup step seeds `default` with the content above when it is missing), and cannot be deleted. It applies when nothing is attached, and it may also be attached like any other policy, so a namespace or table under an ancestor's attachment can go back to the default (and follow its later edits) without a copy.
- **Every version is kept.** Each successful write stores that version's full content immutably; older versions are never changed or removed while the policy exists. `GET /maintenance-policies/{name}/versions/{version}` returns one, so a reconciliation record's "`default` v3" can be opened after v4 exists. Deleting a policy deletes its versions; the records keep the name and number.

## Attachments and inheritance

An attachment binds one policy to one target. **A target has at most one attachment**; attaching a policy to a target that has one replaces it.

| Target type | Path |
|---|---|
| `catalog` | `[catalog]` |
| `namespace` | `[catalog, ns1, …, nsN]` |
| `table` | `[catalog, ns1, …, nsN, table]` |

**The applicable policy of a table** is found by looking, in order, at the table, then its namespace and each parent namespace from deepest to shallowest, then its catalog, and taking the first attachment found; if none, the default policy. The result carries where it was found (`target`) so the console can say "inherited from namespace `prod.sales`".

A table attachment is keyed by the table's UUID, not its name, so a rename keeps it; namespace and catalog attachments are keyed by name. Attachments to a target that does not exist in the catalog are rejected (404) when made; an attachment left behind by a dropped namespace or catalog is harmless and is listed as orphaned in the console.

Attachments are stored by the table-maintenance context in its own SQL table, not in Polaris.

**Changes take effect immediately.** Policies are never copied onto tables. The reconciliation's plan activity resolves the applicable policy every time it plans. After a policy update, attach or detach, the API signals the reconciliation workflow of every managed table whose applicable policy changed, so a changed `reconcile_interval` does not wait for the old timer. The existing `settings_changed` signal and wake reason (`TableReconciliationSignal.SETTINGS_CHANGED`, `WakeReason.SETTINGS_CHANGED`) are renamed `policy_changed` for this; the `paused` and `resumed` signals and wake reasons are removed with pause and resume.

## Changes to existing aggregates

**`Table`** keeps `id`, `name`, `registered_at`, `updated_at`, `operation_states` and `matched_rule_id`. Its status becomes `managed`, `unmanaged` or `dropped`. `selection` (auto/manual), `settings`, `source_preset_id` and the methods `pause`, `resume`, `exclude`, `include_manual`, `exclude_manual`, `include_manually`, `reset_to_auto`, `apply_auto_decision` and `update_settings` are removed, replaced by `manage(rule_id)` and `unmanage()`.

**`TableReconciliation`** gains `policy_name`, `policy_version` and `policy_target` (the attachment's target, or null for the default).

**Deleted:** `TableMaintenancePreset` and everything that serves it; `TableDiscoverySettings`; `MaintenanceSettings` and its per-operation settings (replaced by the policy's value objects); `ConditionCombine`; `TableSelection`.

## API

Modelled on the Polaris policy API; the builder should check Polaris's request shapes for mappings and applicable policies and follow them where they fit.

| Method and path | Does |
|---|---|
| `GET /discovery-rules` | The rules in priority order, with the list's `version`. |
| `PUT /discovery-rules` | Replace the whole list (adds, edits, deletes and reorders at once), given the `version` read; then discover tables. |
| `POST /discovery-rules/preview` | Preview a candidate rule list. |
| `GET /maintenance-policies` | List policies, each with its attachment count. |
| `POST /maintenance-policies` | Create a policy. |
| `GET /maintenance-policies/{name}` | One policy. |
| `PUT /maintenance-policies/{name}` | Replace a policy's content, given the `version` read (409 if stale); `version` increments. |
| `DELETE /maintenance-policies/{name}` | Delete; 409 if attached or `default`. |
| `GET /maintenance-policies/{name}/versions/{version}` | One stored version's content. |
| `GET /maintenance-policies/{name}/mappings` | Its attachments. |
| `PUT /maintenance-policies/{name}/mappings` | Attach to a target; replaces the target's attachment. |
| `DELETE /maintenance-policies/{name}/mappings` | Detach from a target. |
| `GET /tables/{table_uuid}/applicable-policy` | The applicable policy, its version and the target it came from. |
| `GET /applicable-policy?catalog=…&namespace=…` | The same for a catalog or namespace target (as Polaris's applicable-policies takes catalog plus namespace), for the catalog and namespace pages. Served by the table-maintenance context; the console calls it from those pages. |

Removed: `/table-maintenance-presets`, `/table-discovery-settings`, `PUT /tables/{uuid}/settings`, and the table `pause`, `resume`, `include`, `exclude` and `reset-selection` endpoints. A broken invariant answers 422 with a one-line message, a conflict 409, as today.

## Console

- **Discovery rules page** (replaces today's Discovery rules page and discovery switch): an ordered table of rules with priority, an include/exclude tag, the three glob lists as chips, the enabled switch, and edit and delete; "Add rule" opens the same editor. A preview panel beside or below the list shows the tables the current, unsaved list would manage, grouped by the rule that decides them, with counts, and updates as the user edits. Saving says that tables are being discovered.
- **Policies page** (replaces the Presets page): the policies with name, description, version and where each is attached; the default marked as such. The policy editor shows each operation as one section with its enabled switch, its scope where it has one, and two clearly titled groups: "Trigger" (cooldown and conditions, joined by the word "or") and "Execution".
- **Catalog and namespace pages** show the policy attached there, or the inherited one with where it comes from, and let the user attach, replace or detach.
- **Table page** shows the applicable policy and its origin, with the same attach action at table level. The pause, resume, include, exclude and settings controls are removed. Each reconciliation in the history names the policy and version it used.

Follow `src/data-platform/frontend/CLAUDE.md` and the design system as for any console page.

## What is left to the builder

- Exact names of value objects and files, within the project's naming rules.
- The SQL schema for rules, policies, policy versions and attachments, and how the policy content is stored (one JSON column is fine).
- How the preview is computed efficiently enough for the local catalogs; it may load the catalog's table list once per request.
- The console layout details within the description above, and story and test coverage, following the design-system and console rules.
- Whether `TableDiscoveryRules` saves by replacing all rule rows or by row diffs, as long as a save is atomic and versioned.

## References

- Apache Polaris policy management: https://polaris.apache.org/in-dev/unreleased/policy/
- Iceberg Spark procedures (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`): https://iceberg.apache.org/docs/latest/spark-procedures/
- `docs/superpowers/specs/2026-11-10-reconciliation-records-design.md`
- `docs/adr/0005` (bounded contexts), `docs/adr/0009` (pydantic in the domain)
