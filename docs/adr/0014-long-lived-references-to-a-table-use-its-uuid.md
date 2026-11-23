# 14. Long-lived references to a table use its Iceberg UUID

Date: 2026-11-23

Status: Accepted.

## Context

The two bounded contexts name the same table in two ways. The catalog context uses a path: catalog, namespace and table name, which is how the Iceberg REST API finds a table. The table maintenance context uses the Iceberg table UUID (ADR 0001), the required `table-uuid` field of the table's metadata, which stays the same through a rename and a move to another namespace and changes when a table is dropped and created again.

Nothing breaks today. The catalog context stores nothing and reads Polaris on every request, and everything table maintenance stores is keyed by the UUID. But no rule says so. Vernon warns that an identity built from a name breaks when the name changes, and a path does change: the Iceberg REST spec (1.10.1) has `POST /v1/{prefix}/tables/rename`, which may also move a table across namespaces. A future feature (access, comments, owners, lineage) that stored a path would lose its records on the first rename, and nothing would notice. Linear KCL-101 asked for the rule to be written down.

Catalogs and namespaces have no such UUID. The Polaris management API (1.8.0) gives a catalog `type`, `name`, `properties`, timestamps, `entityVersion` and `storageConfigInfo`, and no id; Iceberg REST gives a namespace only its name and properties.

## Considered options

1. **Refer to a table by its UUID wherever the reference outlives a request** (this decision). Paths stay for finding a table, showing it and putting it in a URL.
2. **Refer to a table by its path and rewrite every stored path on a rename.** Every store that names a table would need a rename handler, a missed one fails silently, and a drop followed by a create of the same name would inherit the old table's records.
3. **Leave it to each feature.** That is the situation this record ends.

## Decision

**A reference to a table that outlives a request is its Iceberg table UUID.** That covers a database row, a key, a Kafka payload the backend publishes, a Temporal workflow id, workflow input, signal or activity payload, and any identifier passed to another context. **A path is for lookup, display and URLs.** A request that names a table by its path (an HTTP route, a Polaris event hint, which carries no UUID) resolves it to the UUID before it stores or sends anything.

**A path stored next to a UUID is a display copy and may be stale.** Nothing rewrites it on a rename, so it shows the name the table had when the record was written, and code never finds the table by it alone. Where code does load a stored path as a fallback, it accepts the result only when the loaded table's UUID is the stored one.

**A catalog and a namespace are identified by their path.** They have no UUID, and neither API can rename them: Polaris's `UpdateCatalogRequest` takes only `currentEntityVersion`, `properties` and `storageConfigInfo`, and the only namespace changes in Iceberg REST are create, drop and `POST /v1/{prefix}/namespaces/{namespace}/properties`. **A catalog or namespace dropped and created again under the same name is the same one to the platform**: a policy attached to it applies to the new one, and its discovery settings carry over. This is intended, since a platform user who recreates `sales` means the same `sales`, and it is the opposite of a table, whose new UUID starts with a clean history.

**The catalog context's `TableId` stays a path** because it is the REST locator and the catalog context stores nothing. If it ever stores a reference to a table, that reference is the UUID it already carries.

**Access grants are Polaris's, not ours.** Polaris grants privileges on a table by its name (ADR 0005), and the planned access context sends those grants to Polaris without storing them. If it ever stores a table reference of its own, it follows this record, or its own ADR says why not.

## Consequences

- An audit on 2026-11-23 found one place where a stored path took part in a table's identity: a needs-attention mark compared the policy target it was set under with the path included, so a rename lifted the mark and the next plan ran the failing size again. Marks now compare targets by their key, which for a table is its UUID. No other long-lived reference uses a path as a table's identity. The tables row, its metrics, runs and reconciliation records are keyed by `table_uuid`. A policy attachment to a table has the key `table:<uuid>`. Every table maintenance and reconciliation workflow id is `…:table-uuid=<uuid>`. Signals route by workflow id, and activities receive a table UUID or a run id.
- Three stored copies of a path are display copies, and each is stale after a rename: the `path_json` of a policy attachment, the Temporal static summary fixed when a workflow starts, and the target path in a reconciliation record (a record of that moment, as intended). The `TableName` search attribute is refreshed whenever a plan reports a new name.
- Discovery workflow and schedule ids name a catalog or namespace by its path, which this record allows.
- No architecture test guards this. Whether a stored field holds a path is hard to tell statically, so the rule is held by this record and review.
- A future store that needs to show a table's current name reads it through the UUID (the table maintenance tables row, or a catalog read), not from its own copy.
