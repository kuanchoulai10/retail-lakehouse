# 12. Policies on the catalog hierarchy

Date: 2026-11-19

Status: Accepted.

## Context

The table maintenance context has two kinds of policy that work in different ways. A maintenance policy has a name and kept versions and is attached to a catalog, a namespace or a table; the attachment nearest the table wins. Discovery rules are one platform-wide ordered list of include and exclude rules, each with catalog, namespace and table globs, where the first match wins and no match means unmanaged. A user has to learn two models, the API and the console grow one shape per kind, and discovery cannot be set per catalog or namespace.

The maintenance policy content is also shaped by how the platform runs, not by what the user wants. It is organised as Spark procedures with nested `trigger_policy` and `execution_policy` blocks four levels deep, it holds cooldowns the user should not have to tune, its `priority` only affects compaction, and when a table gets checked is spread through the code where nobody can see or change it.

Linear KCL-82 (one model for every kind of policy) and KCL-83 (maintenance policy content) settled the model between 2026-11-13 and 2026-11-19. KCL-89 moved priority to the table and replaced compaction rounds with one workflow per table, which changed two KCL-83 points on 2026-11-19. This record writes the result down and makes the calls the issues left to the ADR: how to split the aggregates, the API shape, and a few smaller points marked below.

Outside practice compared during the discussion:

- **Apache Polaris policies** attach to a catalog, namespace or table, and the nearest attachment of a type replaces the parent's whole policy of that type. The policy content does not depend on the level.
- **Databricks Unity Catalog**: predictive optimization is enabled, disabled or inherited per catalog and schema; ABAC policies are written `ON CATALOG | SCHEMA | TABLE ... FOR TABLES WHEN <condition>`, with the same condition syntax at every level.
- **Google Cloud Organization Policy** can merge with or replace the parent at each level. It is the most flexible and the hardest to reason about.
- **AWS Organizations** shares one API across policy types: create a policy of a type, attach it to a node.
- **GitHub Actions** keeps `on:` (when a workflow runs) and the jobs (what it does) in one file.

## Considered options

For resolving several policies over a table:

1. Merge or override per level (Google Cloud, `.gitignore`). Expressive, but a reader must evaluate every level on the path to know the result.
2. One ordered platform-wide list (today's discovery rules, CODEOWNERS). One place to look, but a long list and a model unlike maintenance.
3. The nearest attached policy replaces its parents whole, with ordered rules only inside one discovery policy (this decision).

For the aggregates:

1. One `Policy` aggregate with a type field and one shared attachment aggregate. Every policy id becomes a union of kinds, the content needs a discriminated union, and the kinds change together although nothing requires it.
2. One policy aggregate per kind and one shared attachment aggregate. The attachment's policy reference is still a union of id types.
3. One policy aggregate and one attachment aggregate per kind, sharing the target value object and the resolution service (this decision).

For the maintenance policy layout (KCL-83):

1. Grouped by concern (`layout`, `history`).
2. GitHub Actions rules (`on:` plus `jobs:` with `if:` conditions), which needs a condition language.
3. Profiles (`profile: streaming` with overrides), which the platform would have to maintain.
4. A target half and an optional tuning half (`target:` plus `tuning:`).
5. Target state with `on:`, one block per operation holding its `target` and optional `options` (this decision; the user wanted each operation's target and its arguments side by side).

## Decision

### One resolution rule for every kind

- **Two kinds of policy: discovery and maintenance.** There is no reconciliation policy; when a table is checked is the maintenance policy's `on:` block (KCL-81 is replaced).
- **A policy of each kind has a name, an id and kept versions**, and can be attached to any number of catalogs, namespaces and tables. A target holds at most one attachment per kind, and an attachment always means the policy's latest version.
- **The nearest attachment wins and replaces its parents whole**: table, then namespace (deepest first), then catalog, then the platform default. Nothing merges.
- **A table is attached by its Iceberg uuid** (ADR 0001), so a renamed or moved table keeps its attachments, and a table that is not managed yet can carry them.
- **The platform defaults are fixed policies.** The default maintenance policy keeps `mp-00000000000000000000000000` (ADR 0011). The default discovery policy is `dp-00000000000000000000000000`, with no rules and "unmanaged" when nothing matches, and it cannot be edited: managing tables always means attaching a discovery policy somewhere (my call).

### Discovery policy

- **Content: ordered rules plus a no-match outcome.** Rules are read top to bottom; the first matching rule decides "manage" or "do not manage". Every policy carries its own outcome for when no rule matches, because it replaces its parents and cannot fall back to them. A policy attached to one table is usually just "no rules, manage".
- **A rule's match is a set of conditions, all of which must hold** (my call: at least one condition per rule). A condition names the attribute it reads and how it matches. Today there are two, a namespace glob and a table name glob, with the glob semantics of the current discovery rules. Labels and table properties are later conditions of the same shape, with no change to the structure.
- **Conditions do not depend on the level.** The level a policy is attached to only decides which tables are matched against it. A condition that cannot have an effect there (a namespace glob on a policy attached to a namespace) is allowed; the console shows a hint.
- **Which catalogs are scanned is derived.** A catalog is scanned when some discovery policy attached to it, or to a namespace or table inside it, can resolve to "manage" (a manage rule or a "manage" no-match outcome). The scan interval stays a platform setting.
- **Rules keep their `dr-` ids; the policy uses `dp-`.** The discovery policy replaces the `TableDiscoveryRules` aggregate. Existing rules are not converted; the cluster is rebuilt.

### Maintenance policy

```yaml
on:
  schedule: { every: 1h }
  catalog_commit: { debounce: 5m }
dry_run: false
rewrite_data_files:
  target:  { reducible_files: { at_most: 5 }, per: partition }
  options: { strategy: binpack, min_input_files: 2 }
rewrite_manifests:
  target:  { small_manifests: { at_most: 5 } }
  options: { use_caching: true }
expire_snapshots:
  target:  { min_snapshots_to_keep: 10, max_snapshot_age: 1d }
remove_orphan_files:
  target:  { older_than: 3d }
```

- **`on:` says when the table is checked.** `schedule` is required and only its interval can change, so a table whose events are lost is still checked. `catalog_commit` is optional, debounce 5 minutes by default; leaving it out means commits do not trigger a check. A manual run, a manual check, a policy change and a table becoming managed always trigger a check and are not written in `on:` (my call for the last two, which the first KCL-83 sketch listed as `policy_changed` and `discovery_scan`).
- **One block per operation; leaving a block out means the operation is not done.** The four operations run in the fixed order shown (KCL-89).
- **`target` is the state the table should be in.** Names follow Iceberg table properties where one exists (`min_snapshots_to_keep` for `history.expire.min-snapshots-to-keep`, `max_snapshot_age` for `history.expire.max-snapshot-age-ms`) and Iceberg procedure arguments or our existing names otherwise (`older_than`, `reducible_files`). `reducible_files` is the existing count: data and delete files minus the total size divided by the target file size, rounded up. `small_manifests` counts manifests under the table's `commit.manifest.target-size-bytes` (8 MiB when unset).
- **The target file size is the table's `write.target-file-size-bytes`**; the policy does not hold one. Where a target overlaps another table property (`history.expire.*`), the policy's value is passed to the procedure and wins (my call: the policy is where the user states the target).
- **`options` are optional procedure arguments.** Only arguments the Iceberg procedure has are accepted, and a value already in `target` cannot be set again in `options`. What is not written, the platform decides.
- **`dry_run` is top level.** There is no `importance` or `priority`: priority P0 to P3 is the table's own setting (KCL-89).
- **Cooldowns, failure back-off, attempt timeouts, retries and concurrency are platform settings**, not policy.
- **Removing orphan files has no target the platform can measure cheaply** (counting orphans means listing storage), so it is due on a platform interval, 7 days by default.

### Compacting only the partitions that need it

With `per: partition`, each partition is compared with `reducible_files.at_most` on its own, and only the partitions over it are compacted, passed to `rewrite_data_files` as `where` clauses (`build_partition_filters`, which renders `days(ts)`, `bucket` and the other transforms). With `per: table` the table's total is compared and the whole table is rewritten. Two platform settings shape the selection:

- **At most N partitions per Spark job** (10 by default), those over the target for the longest wait first (oldest first), then those with the most reducible files. The rest are still over the target at the next check, and a partition over the target for the longest wait goes first (see the 2026-11-21 note below).
- **A partition written to recently is skipped** (a quiet period of a few minutes since its last write), unless it has been over the target for longer than a maximum wait (1 hour by default).

There is no scoring, no cost-benefit ranking and no compaction round (KCL-89). The run records the `where` clauses it passed, so each run shows which partitions it compacted (KCL-80).

2026-11-21 note (KCL-94): the order alone could leave a cold partition just over the target behind the cap for ever, while busier ones kept growing back above it. Under the cap, a partition that has been over the target for the longest wait (1 hour by default) goes first, oldest first, and the others follow by reducible files. This is still a plain sort, not a score. A partition left out is therefore taken at a later check once it has been over the target for the longest wait; with a longest wait of 0 every partition counts as overdue and the cap takes the oldest first.

### Aggregates and API

- **Aggregates in table maintenance:** `TableMaintenancePolicy` and `TableMaintenancePolicyAttachment` stay; `TableDiscoveryPolicy` and `TableDiscoveryPolicyAttachment` replace `TableDiscoveryRules`. `PolicyTarget` and the nearest-attachment resolution move to the context's `shared` model, so a third kind adds a policy and an attachment aggregate and reuses both. One attachment per target and kind is a unique constraint in the database (ADR 0011).
- **The API has the same shape for every kind:**

| Resource | Paths |
|---|---|
| Policies of a kind, by name | `/v1/maintenance-policies`, `/v1/discovery-policies`, each with `/{name}` and `/{name}/versions/{version}` |
| Where a policy is attached | `/v1/{kind}-policies/{name}/attachments` |
| What applies to a table, and from which level | `/v1/tables/{table_uuid}/effective-policies`, one entry per kind, for managed and unmanaged tables |

  A collection per kind, rather than one `/v1/policies?type=`, keeps each kind's body its own schema in OpenAPI and lets names be unique per kind. `effective-policies` replaces both `applicable-policy` routes, and `/v1/discovery-rules` goes.

2026-11-21 note (KCL-71): the discovery policy is built.

- **A condition is `{attribute, operator, values}`**, modelled on Kubernetes `matchExpressions`, so labels and table properties later add an attribute or an operator, not a new structure. The attributes are `namespace` and `table_name`, the only operator is `glob`, and a condition holds when any of its values matches.
- **The outcomes are `manage` and `unmanage`**, the words of the table's own statuses; the console says "Manage" and "Do not manage".
- **Attach is `PUT /v1/discovery-policies/{name}/attachments` with `{"target": {"type", "path"}}` and detach is `DELETE /v1/discovery-policies/{name}/attachments/{attachment_id}`**, by the attachment's `da-` id. A request body on `DELETE` has no defined semantics (RFC 9110 §9.3.5), and detaching by id also works for an orphaned target. KCL-98 gives maintenance attachments the same shape.
- **A target must exist when it is attached, but it may be empty.** An empty catalog or namespace may be attached, since the first place a discovery policy goes is often an empty catalog; a target that does not exist is 404. The same check now serves maintenance attachments, and an attachment is orphaned only when its target no longer exists.

## Consequences

- One rule explains every policy on a table: walk up from the table to the first attachment. `effective-policies` shows the answer and the level it came from.
- A namespace that attaches its own policy no longer gets its catalog's rules and must repeat what it shares with them. The discussion accepted this because exclusion conventions differ per namespace.
- Discovery can be set per catalog and namespace, and the exception-to-an-exception case (`orders_tmp` managed although `*_tmp` is not) is two ordered rules in one policy.
- A table owner writes the state a table should be in and when to check it; cooldowns and scheduling stay with the platform, and anyone who wants to tune a procedure still can through `options`.
- Without a scheduler-wide ranking, a table with many bad partitions is caught up over several checks, N partitions at a time.
- `table_discovery_rules` leaves the aggregate list in the backend `CLAUDE.md` and ADR 0005, and the context's `AGGREGATE_SQL_PACKAGES` changes. The console's policy and discovery pages, the e2e scripts and the reconciliation that reads the old content all change with it.
- No data is migrated; old policies, rules and attachments are dropped when the cluster is rebuilt.
