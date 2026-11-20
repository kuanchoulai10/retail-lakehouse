# 13. Table metrics in the database and Prometheus

Date: 2026-11-20

Status: Accepted.

## Context

The table page Overview shows how a table changes over time: how many files it holds, how large it is, how many rows, how many files a compaction could remove, how many manifests and snapshots. The cards show the table now; the charts show the last hour, three hours or six hours. Iceberg's own snapshot history cannot draw them. `expire_snapshots`, which the platform runs itself, removes the old snapshots, and the manifest and snapshot counts are not in a snapshot's summary.

The numbers come from the reconcile, which already reads every partition's statistics to measure the table. Prometheus is the usual store for a trend, but it pulls: it asks a target for its current state on a fixed interval. The reconcile runs once an hour by default and on commit windows and manual runs, so something has to hold the latest numbers between those runs and hand them over when Prometheus asks. Linear KCL-69 settled the metric list, the six-hour retention and the three ranges on 2026-11-17 and 2026-11-19; this record writes down how the numbers reach Prometheus and how the console reads them back.

## Considered options

For getting the numbers into Prometheus (KCL-69, 2026-11-17):

1. **An exporter that reads the database** (this decision). Every reconcile saves the table's latest metrics in the database, one row per table, and an API endpoint prints them in the Prometheus text format when Prometheus scrapes it. This is the pattern of kube-state-metrics, which reads the state of Kubernetes and exposes it, and of postgres_exporter, which queries when it is scraped.
2. **Remote write from the reconcile.** It works, but Python has no official remote write package, so it would add protobuf and snappy dependencies and an encoding of our own. One point an hour needs `last_over_time` in every query to draw a line, and Prometheus refuses points that are too old or out of order.
3. **Numbers in the worker's memory, scraped from the worker.** A restart loses them, and several workers would export the same table twice.

For how the console reads the trends:

1. The browser queries Prometheus. Grafana has deprecated this, and it would expose Prometheus and let a browser send any query.
2. The backend queries Prometheus for the browser (this decision), the way OpenShift's console and Kiali do.

## Decision

**A table's metrics are saved by every reconcile that observes the table and forgotten by every reconcile that skips it.** The plan service saves the metrics right after it records the last commit, whether the run is manual, scheduled or a dry run. When it skips a table because the table is unknown, dropped, unmanaged or no longer in the catalog, it deletes the row. The store only moves the observation time forward, so a retried activity with an older observation never replaces newer numbers. **A failure to measure, save or delete the metrics is logged and never stops a plan:** the metrics only show the table's state, so they never cost the table its maintenance.

**`GET /v1/table-metrics` is the exporter.** It prints 17 gauge series per managed table, in base units and without timestamps, and it is hidden from the OpenAPI schema because Prometheus is its only caller. It reads the database on each scrape and exports only tables whose status is `managed`, so a table that leaves maintenance disappears from it even when no plan ran to delete its row. The names of the namespace and the table live only in `iceberg_table_info`; the other series carry `table_uuid`, so a rename does not split a series.

**A small Prometheus of its own stores the series for six hours.** Wave 26 runs Prometheus in the namespace `table-metrics` with a 2 Gi volume, a retention of six hours or 1 GB, and one scrape job that targets the API Service directly, so several API replicas never duplicate a series. It is separate from the paused `10-kube-prometheus`, has no route through the gateway and is never exposed.

**The backend reads the trends and the browser never sends a query.** `GET /v1/tables/{uuid}/metrics?range=1h|3h|6h` sends one fixed `query_range` selector for the table's uuid, only after the tables repository knows the uuid, and shapes the answer into one list of points per metric, with `null` where Prometheus has no value. A Prometheus that is down gives 502 with its reason. The cards come from `GET /v1/tables/{uuid}/metrics/current`, which reads the saved row and does not need Prometheus.

## Consequences

- A line is flat between reconciles. The metrics move only when a plan runs: on the policy's schedule, when a commit window closes, and on a manual run, `reconcile_now`, `policy_changed` or `table_managed`. A policy with no `catalog_commit` can show a flat one-hour chart.
- A finished maintenance run does not trigger a fresh check. After a compaction, the cards and charts still show the files before it until the next check: the compaction's own commit window closing, the schedule, or a manual reconcile. Unchanged cards right after a compaction are not a failed compaction.
- The cards read the database and the charts read Prometheus, so the two can differ by up to one scrape plus one step: the chart's last point is now rounded down to the step, and Prometheus holds a value only after its next scrape. That is about 1 minute at 1 h and about 3.5 minutes at 6 h.
- Prometheus memory grows with the number of managed tables, 17 series each. 20 000 tables need about 1 to 2 GiB and a scrape response of tens of megabytes, so a platform of that size needs a longer scrape interval or sharding. The minikube Prometheus is capped at 1 GiB and fits a small number of tables.
- A rename keeps the series and changes the labels of `iceberg_table_info`, so a chart follows the table across it.
- The reconcile gains a write per observation and the table maintenance database gains one table; `create_schema` creates it, and the cluster is rebuilt instead of migrated.
- No new dependency in the backend or the console: the exposition is plain text and the query uses the HTTP client the backend already has.
- The trend endpoint adds the metrics settings `GLAC_METRICS__PROMETHEUS_URL` and `GLAC_METRICS__QUERY_TIMEOUT_SECONDS`.
- The `/health` and `/storage` endpoints of a table are removed; the saved metrics replace them, and no console page called them.
