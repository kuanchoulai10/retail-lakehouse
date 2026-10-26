# 3. Catalog events are hints; the catalog is the source of truth

Date: 2026-10-24

Status: Accepted

## Context

Polaris 1.8.0 publishes catalog events to the Kafka topic `polaris-catalog-events`. The control plane uses them to find new tables quickly and to react to commits. Sampling the topic showed that the events are incomplete for this purpose: `BEFORE_CREATE_TABLE` has no table name, and a Trino-created table showed up as `AFTER_UPDATE_TABLE` commits rather than `AFTER_CREATE_TABLE`. Events can also be lost (consumer downtime, a poison record that is skipped), duplicated or reordered.

## Considered options

1. Treat events as facts and apply them directly to the registry (create, rename, drop).
2. Ignore events and rely only on periodic discovery.
3. Treat events as hints: an event only names a table or namespace to look at, and every decision is made from a fresh catalog read. Periodic discovery is the safety net.

## Decision

Option 3. The event consumer maps table-level events (`AFTER_CREATE_TABLE`, `AFTER_UPDATE_TABLE`, `AFTER_DROP_TABLE`, `AFTER_REGISTER_TABLE`, `AFTER_RENAME_TABLE`) to a table hint, and `BEFORE_CREATE_TABLE` without a table name to a namespace discovery request. The hint use case loads the table from the catalog: an unknown UUID is evaluated against the discovery rules and registered; a known UUID under a new name is renamed; a known table gets a `table_updated` signal; a table missing from the catalog triggers a catalog-wide discovery, which alone may mark tables `DROPPED`. A Temporal schedule per catalog (`table-discovery:catalog={catalog}`) runs discovery every 10 minutes. Every record is committed after handling, including failed ones; a failing hint is tried at most 3 times.

## Consequences

- Missing, duplicate or reordered events cannot corrupt the registry, because every decision comes from the catalog.
- A lost hint delays maintenance by at most one discovery interval.
- Each hint costs a catalog read. Under heavy commit traffic this is one `load_table` per commit, plus a reconcile wake that cooldowns usually turn into an empty plan.
- Maintenance commits also produce update events. Cooldowns and the one-run-per-table rule keep them from looping.
- Kafka is used only as an event source, never as a maintenance request queue.
