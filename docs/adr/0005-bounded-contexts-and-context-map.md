# 5. Bounded contexts and context map

Date: 2026-11-07

Status: Accepted

## Context

The backend today has one bounded context, table maintenance. Our database is its source of truth. The platform will also manage catalog objects (catalogs, namespaces, tables, views) and access control (principals, principal roles, catalog roles, grants). For both of these, Polaris is the source of truth.

Putting three models with different sources of truth on one aggregate axis would blur the boundaries that the architecture tests protect. The backend therefore adds a context level above the aggregate axis.

No code implements this ADR yet beyond the move of the existing code into `context/table_maintenance/`. The `catalog` and `access` contexts come in a later project.

## Considered options

1. Keep one context and add the new aggregates beside the existing ones.
2. Split into contexts that share a common domain package for types such as the table UUID.
3. Split into independent contexts. They share only `base`, and they link by identifier values.

## Decision

Option 3. The backend has three contexts under `context/<name>/`:

| Context | Owns | Source of truth |
|---|---|---|
| `table_maintenance` | `CatalogDiscovery`, `Table`, `TableMaintenancePolicy`, `TableMaintenancePolicyAttachment`, `TableDiscoveryPolicy`, `TableDiscoveryPolicyAttachment`, `TableMaintenanceRun`, `TableReconciliation` | Our database |
| `catalog` | Catalogs, namespaces, tables, views | Polaris |
| `access` | Principals, principal roles, catalog roles (grants live inside the catalog-role aggregate) | Polaris |

Updated 2026-11-12: maintenance presets and discovery settings were replaced by versioned maintenance policies with their attachments and by one versioned discovery rules list (plan `docs/superpowers/plans/2026-11-11-maintenance-policy-and-discovery-rules.md`).

Updated 2026-11-20 (KCL-93): the maintenance flow is one reconciliation per table, which starts one maintenance workflow per table (`table-maintenance:table-uuid={uuid}`) whose Spark jobs go straight to Volcano queues. The global compaction round, the compaction candidates and the admission workflow were removed, so the `CompactionCandidate` and `CompactionRound` aggregates no longer exist.

Updated 2026-11-21 (KCL-71): the one discovery rules list became versioned discovery policies attached on the catalog hierarchy (ADR 0012), so `TableDiscoveryRules` is replaced by the aggregates `TableDiscoveryPolicy` and `TableDiscoveryPolicyAttachment`.

Relations between the contexts:

- The maintenance `Table` and the catalog table are different models of the same thing. They are linked by the Iceberg table UUID (ADR 0001), as an identifier value and not as a shared class. Any reference to a table that outlives a request uses that UUID (ADR 0014).
- Maintenance conforms to the catalog. The catalog is the truth and maintenance follows it (ADR 0003).
- `access` does not depend on `catalog`. A grant names its target by catalog, namespace and table name, and Polaris rejects a target that does not exist. If `access` later needs to check targets itself, it does so through its own outbound port.

Rules between contexts:

- Contexts are independent. A context's `application` imports no other context.
- A context may use another only from its own outbound adapters. The adapter implements a port defined in the consuming context's own language. It calls the other context's inbound port (use case) and maps the output into the consuming context's types. This is an anti-corruption layer.
- No code is shared between contexts beyond `base`. There is no `context/shared`. Each context keeps its own types, for example its own table-UUID value object.
- `bootstrap` may import every context. `base` imports no context.

## Consequences

- A context can be changed, tested and reasoned about without reading the others.
- The same idea (a table, a UUID) is modelled more than once. This is deliberate duplication, and it costs some mapping code in adapters.
- The architecture tests run the same rules for every context. Context independence is enforced by a contract or test, which stays green with one context and fails when a second context reaches into another's internals.
- Cross-context use cases need an adapter and a port on the consuming side. This is more code than a direct import.
