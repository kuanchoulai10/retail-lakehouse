# Single `Table` aggregate, no read-model split

We considered modelling the Iceberg table as two objects: a `Table` read-model (Iceberg's truth, queried on demand) plus a `ManagedTable` aggregate (our DB record holding only management metadata). We collapsed back to a single **`Table`** aggregate that owns both Iceberg-side state (properties, schema, current snapshot id) and tool-side metadata (enrolled_at, enrolled_by). The repository is the only seam: load fetches from the catalog adapter, save flushes accumulated mutations atomically (a single underlying `ALTER TABLE` covers batched property changes — Iceberg commits are atomic).

## Considered Options

- **Read-model + `ManagedTable` split.** Cleanly separates "Iceberg's truth" from "our intent". Rejected: every mutation use case had to coordinate two objects and bypass the aggregate to call a gateway, which violated DDD's "aggregate is the gatekeeper" principle. Operator pushback: "the table IS the aggregate; we exist to manage it."
- **Single aggregate** (chosen). Aggregate is the single entry point for any change to the table. Repo abstracts away whether the backing store is Polaris direct, Trino, or something else.

## Consequences

- Every `Table` load talks to the catalog adapter — not free. CQRS escape hatch: queries that don't need the full aggregate (e.g. browsing catalog contents that haven't been enrolled) go through a separate lightweight read path.
- The aggregate carries Iceberg-side fields that **the catalog is the source of truth for**. Stale loads are mitigated by Iceberg's MVCC commit protocol — a stale `ALTER` is rejected at commit time.
- Tool-side fields (status, enrolled_by) live in our DB; Iceberg-side fields live in the catalog. The repo joins the two on load and writes both on save. Cross-store atomicity is best-effort: write Polaris first (the external/expensive one), then DB; reconcile via outbox if DB write fails.
- Choice of catalog backing (Polaris-direct vs Trino-mediated) is deliberately deferred — the aggregate boundary makes it an adapter-layer concern.
