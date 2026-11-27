# 18. Discovery rules and policies held by places

Date: 2026-11-27

Status: Accepted. Supersedes parts of ADR 0012 (listed under "What this supersedes").

## Context

ADR 0012 gave both kinds of policy one resolution rule: the nearest attachment to a table wins and replaces its parents whole. That rule stands. Three other parts of 0012 did not work in practice.

The first problem was the discovery policy's content. It was ordered rules of `{attribute, operator, values}` conditions over `namespace` and `table_name`, read first match first, plus a `no_match_outcome`. The owner found the words (condition, attribute, operator, outcome, match) hard to read. Conditions that do not depend on the level meant nothing on a policy attached to a table, and a fixed default discovery policy that could not be edited was one more thing to explain.

The second problem was the attachment aggregates. `TableDiscoveryPolicyAttachment` (`da-`) and `TableMaintenancePolicyAttachment` (`pa-`) each put a policy on a `PolicyTarget`. "Where is this table's policy" therefore needed a second lookup by target, and nothing tied an attachment to the place it named. A catalog or namespace had no record of its own in table maintenance, so it had no version that could protect it against two writers.

The third problem was discovery scheduling. Each scanned catalog had its own Temporal schedule. Every policy change synced the schedules (`apply_discovery_change`, `SyncDiscoverySchedules`), and a catalog that stopped being scanned got a `schedule-retired` final scan. Two changes at the same moment could leave the schedules wrong until the next change or worker start.

Linear KCL-116 (discovery rules) and KCL-117 (policies on catalogs, namespaces and tables, one schedule) settled the design on 2026-11-27. Their decisions are the comments dated 2026-11-27. The implementation plan made eleven rulings where the issues were silent, and four more were made while it was built. This record writes down the ones that are design.

Outside practice compared:

- **`.gitignore`** and **GitHub `CODEOWNERS`** read their patterns top to bottom, and the last matching pattern decides. The exception to an exception is written as a later line, with no negation syntax inside a pattern.
- **Apache Polaris policies** attach to a catalog, namespace or table, and the nearest one of a type replaces its parent's (the rule ADR 0012 adopted).
- **Optimistic offline lock** (Fowler, *Patterns of Enterprise Application Architecture*) and **Kubernetes `resourceVersion`**: a write names the version it read, and a stale write is refused, never merged. Vernon (*Implementing Domain-Driven Design*) keeps the version on the aggregate, the consistency boundary.
- **Temporal** offers schedules with an overlap policy, child workflows with a parent close policy, signal-with-start, and continue-as-new.

## Considered options

For the discovery policy's content:

1. Keep conditions and a no-match outcome, and drop the default policy only.
2. A default action plus include and exclude lists. This is asymmetric: an include list under a default of "include" means nothing.
3. Rules whose pattern depends on the level they are attached to. A rule would then read differently on a catalog than on a table.
4. Ordered `include` / `exclude` rules on the table name alone, where the last match decides and no match means not managed (this decision).

For where an attached policy is stored:

1. One attachment aggregate per kind (ADR 0012, as built).
2. Three mapping tables, `catalog_policies`, `namespace_policies` and `table_policies`, each with a kind column (KCL-117's first sketch). One column cannot hold a foreign key to two policy tables.
3. Two nullable foreign-key columns, `discovery_policy_id` and `maintenance_policy_id`, on the rows of the places themselves (this decision).

For scheduling discovery:

1. One schedule per scanned catalog, synced on every change (as built).
2. One schedule whose round waits for every catalog's scan. With overlap `SKIP`, one slow catalog would make the next round skip every catalog.
3. One schedule whose round starts one scan per catalog and does not wait (this decision).

For a scan request that arrives while that catalog is already being scanned:

1. Join the running scan (`USE_EXISTING`). The change is then applied only from the next round, because the scan read the policies at its start.
2. A new workflow id per change. This allows two scans of one catalog at once, which "one running scan per catalog" forbids.
3. Signal the running scan to scan once more when it finishes (this decision).

## Decision

### A discovery policy is ordered include and exclude rules (KCL-116)

- **A rule is an action, `include` or `exclude`, and a table name pattern.** The pattern matches the table name alone, with `fnmatchcase` (case-sensitive glob), whatever level the policy is attached to. `*` matches every table, even on a policy attached to one table.
- **The last matching rule decides.** No match means the table is not managed. The exception to an exception (`include *`, `exclude *_tmp`, `include orders_tmp`) is three lines.
- **A policy holds at least one rule, and that is its only content rule.** A policy of exclude rules only is allowed. A policy keeps its `description` (ruling 6), versioned with its rules.
- **Rules have no ids.** `dr-` goes. A version page compares two versions as `(action, pattern)` pairs along their longest common subsequence, so a moved rule reads as removed and added.
- **There is no default discovery policy.** `dp-00000000000000000000000000` goes. A table with no discovery policy on its walk is not managed, and nothing decided it. The maintenance default (`mp-00000000000000000000000000`) stays.
- **What decided a table is `decided_by`:** the policy id, its version and the 1-based position of the deciding rule. The position is null when the policy applies but no rule matched, and `decided_by` is null when no policy applies. A change of `decided_by` alone is saved and sends nothing (`DECISION_CHANGED`, ruling 11).
- **A catalog is scanned while a discovery policy is attached in it**, to the catalog, a namespace or a table, whatever its rules hold, and while it still holds a managed table. That scan unmanages tables that nothing manages any more, and the catalog then drops out. A catalog where no attached policy can include anything unmanages its stored tables without reading the catalog.

### Places hold their policies (KCL-117)

- **`Catalog`, `Namespace` and `Table` each hold at most one policy of each kind** (ruling 1). They hold the ids as `discovery_policy_id` and `maintenance_policy_id`, columns with a foreign key on the `catalogs`, `namespaces` and `tables` rows. The ids change only through the aggregate's `attach_*` and `detach_*` methods. `Catalog` and `Namespace` are table maintenance's own aggregates, not the catalog context's (ADR 0005). A catalog is identified by its name, and a namespace by its catalog and levels, joined by U+001F.
- **There is no attachment aggregate, no attachment id and no `attached_at`** (ruling 7). The read model "where is this policy attached" is one `UNION ALL` over the three tables (`PolicyPlacementsStore`).
- **The resolution rule of ADR 0012 is unchanged.** The walk is the table under its current name, then its enclosing namespaces deepest first, then its catalog. The first place that holds a policy of the kind replaces every place above it.
- **A detach names the place, not an id.** The routes are `DELETE /v1/{kind}-policies/{name}/attachments?target_type=&path=…`, with the path repeated once per part. A request body on `DELETE` has no defined semantics (RFC 9110 §9.3.5), which ADR 0012 already weighed. A detach does not read Polaris. A table is found among the live rows of its name, preferring the row that holds the policy. A place that does not hold the policy is 404.
- **Deleting a policy that is still attached anywhere is refused** with a 409 that names each place. The foreign keys refuse a delete that races an attach.
- **A dropped table holds no policy** (ruling 4). An Iceberg uuid never comes back, so keeping the ids would only stop the policy from ever being deleted.
- **A catalog or namespace that left Polaris keeps its record until its policies are detached** (ruling 5). The attachment list marks it `orphaned`, and it detaches like any other place.
- **A table attached to before discovery saw it is `undecided`** (ruling 10). The attach registers the table, and the scan the attach asks for decides it. A catalog scan already running when the attach registered it neither drops nor retires the row, since its listing may predate the table (2026-11-28: a row registered at or after a scan started is left alone by that scan's drop and retire passes). An undecided table is never planned, measured or exported. Only a discovery decision moves it on. A move to `unmanaged` sends no table change, since no maintenance workflow exists to stop.
- **A namespace level that holds a `.` cannot hold a policy.** The attach answers 422. A table names its namespace dot-joined, so the namespaces enclosing it are found by splitting on dots, and a policy on such a level would silently never apply. Refusing it is safer than accepting a policy that never applies.

### Every place is saved with optimistic locking

- **`Table`, `Catalog` and `Namespace` carry a `version`** (ruling 2). A repository `update` writes only when the stored row is still at the version read. It moves the version on by one and returns the aggregate read back. A table version was needed first, because the worker writes table rows while a person attaches a policy to them. A catalog version keeps one person's discovery attach from overwriting another person's maintenance attach on the same catalog.
- **A stale save raises `ConcurrentUpdateError`, an application exception of its own, not a `ConflictError`** (ruling 3). A lost race is worth retrying, because the retry reads the row again. Temporal activities therefore retry it (they treat `ConflictError` as final), and the event consumer retries it too. The web answers 409. Inside a catalog scan, the raced table is logged and counted `skipped`, and the next scan decides it.

### One discovery schedule, one scan per catalog

- **One schedule, `table-discovery`, starts a round every `discovery.interval_seconds` (600 by default) with overlap `SKIP`** (ruling 8). The round, `TableDiscoveryRoundWorkflow`, lists the scanned catalogs. It then starts one child `TableDiscoveryWorkflow` per catalog under `table-discovery:catalog={catalog}` with `ParentClosePolicy.ABANDON`, and skips a catalog whose scan is already running. It does not wait for its children, so one slow or unreadable catalog never makes the next round skip the others.
- **The worker start ensures the schedule**: it creates the schedule, or updates its interval and action and unpauses it. A failure stops the start. Nothing syncs schedules on a policy change any more. `apply_discovery_change`, `SyncDiscoverySchedules`, the per-catalog schedules and the `schedule-retired` final scan are gone.
- **A change asks for a scan of the smallest place that covers it**, best effort (ruling 9). An attach or detach on a catalog scans that catalog. One on a namespace scans the namespace and every namespace under it (2026-11-28: the scan walks that subtree, so a parent namespace's tables in `a.b` are decided at once), and one on a table scans its namespace. A policy revision scans each catalog it is attached in. A request that cannot be sent is logged, and the change stands.
- **A catalog scan request is a signal-with-start of `table-discovery:catalog={catalog}` with the signal `request_rescan`.** It starts the scan when none is running. Otherwise the running scan, which read the policies at its start, scans once more when it finishes, as a new run of the same id through continue-as-new. Requests that arrive during one run fold into one more scan.
- **A namespace scan request also asks the running catalog scan to rescan.** It starts its own scan under `table-discovery:catalog={catalog}:namespace={namespace}:trigger=policy-changed:change={id}`. It then sends `request_rescan` as a plain signal to `table-discovery:catalog={catalog}`, and ignores the reply when no scan is running. Without this signal, a catalog scan that read the policies before the change could undo the namespace scan's decision until the next round.

### What this supersedes

From ADR 0012, these points no longer hold:

- "The platform defaults are fixed policies", for discovery: there is no default discovery policy. The maintenance default stays.
- "Content: ordered rules plus a no-match outcome", "A rule's match is a set of conditions" and the 2026-11-21 note's condition shape and `manage` / `unmanage` outcomes: they are replaced by include and exclude rules, last match deciding.
- "Conditions do not depend on the level": a rule now matches the table name, the same at every level.
- "Which catalogs are scanned is derived" (from policies that can resolve to "manage"): a catalog is now scanned while any discovery policy is attached in it or it holds a managed table.
- "Rules keep their `dr-` ids": rules have no ids.
- "Aggregates and API", the attachment aggregates, and the notes' `da-` / `pa-` detach by `attachment_id`: places hold the policies, a detach names the place, and the effective-policies entries carry no `attachment_id`.

The resolution rule, the maintenance policy and its content, and the API's collection per kind all stand.

## Consequences

- One read answers what a place holds, and one aggregate holds both of its policies, so the two kinds cannot disagree about a place. The cost is three rows per place kind, and a catalog or namespace record that outlives its Polaris object until its policies are detached.
- A scan reads its catalog's record and every namespace of the catalog once, then decides every table from them.
- A namespace or table change made while its catalog is being scanned costs one extra scan of the whole catalog.
- A worker that misses a policy change still converges within one round. No schedule state can drift from the policies, so the worker start has nothing to reconcile.
- An attach to a table discovery never saw creates a table row before any scan. The console shows such a table as `Undecided` and lists it by default.
- A namespace whose level holds a dot cannot carry a policy until tables store their namespace as levels (`docs/agents/known-follow-ups.md`).
- The `table_discovery_policy_attachments` and `table_maintenance_policy_attachments` tables, the `dr-`, `da-` and `pa-` prefixes (ADR 0011) and the per-catalog schedules are gone. No data is converted, so the cluster is rebuilt.
- The aggregate lists in the root `CLAUDE.md`, the backend `CLAUDE.md` and ADR 0005 now name `Catalog` and `Namespace` and no attachment aggregate.

## References

- Linear KCL-116 and KCL-117, and their comments titled 決定（2026-11-27）.
- ADR 0012, Policies on the catalog hierarchy (the resolution rule kept here).
- ADR 0005, Bounded contexts (table maintenance's own `Catalog` and `Namespace`).
- gitignore, the last matching pattern decides: https://git-scm.com/docs/gitignore
- GitHub, About code owners (the last matching pattern takes precedence): https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Python `fnmatch.fnmatchcase`: https://docs.python.org/3/library/fnmatch.html
- Martin Fowler, Optimistic Offline Lock: https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html
- Kubernetes API concepts, resource versions: https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions
- Vaughn Vernon, *Implementing Domain-Driven Design*, chapter 10 (aggregates as consistency boundaries).
- Temporal schedules and overlap policies: https://docs.temporal.io/schedule
- Temporal parent close policy: https://docs.temporal.io/parent-close-policy
- Temporal signal-with-start: https://docs.temporal.io/sending-messages#signal-with-start
- Temporal continue-as-new: https://docs.temporal.io/workflow-execution/continue-as-new
- RFC 9110 §9.3.5, DELETE: https://www.rfc-editor.org/rfc/rfc9110#section-9.3.5
