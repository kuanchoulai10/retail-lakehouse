# 16. The Spark adapter writes Iceberg procedure calls

Date: 2026-11-24

Status: Accepted. Supersedes the placement in ADR 0004 (where clauses rendered in the domain); its escaping rule stands.

## Context

A maintenance run calls one Iceberg Spark procedure. Until now the backend decided that call in its own words and wrote it in Iceberg's at once: `build_partition_filters` in the domain rendered each selected partition spec as a Spark SQL `where` clause (escaping per ADR 0004), and each operation's options value object had `procedure_arguments` and `procedure_options` methods that returned Iceberg's hyphenated option names, decided which values go in the `options` map, and wrote times as ISO text. The run then stored those strings, `filters` and `procedure_args`, and every layer above passed them through.

That put the engine's call format in the domain. Adding an option meant writing its Iceberg spelling inside a policy value object; a run's record showed `min-input-files` and `(`region` = 'eu')` instead of the setting and the partition it was about; and a second engine, or a change in Iceberg's spelling, would have reached the domain model. Linear KCL-109 (finding F3) asked for the domain to decide only what a job does, and for the Spark adapter alone to write how Spark is asked to do it, with the `CALL` Spark runs unchanged by one character.

## Decision

- **The domain decides what a job does, as typed content.** `RewriteDataFilesJobContent`, `RewriteManifestsJobContent`, `ExpireSnapshotsJobContent` and `RemoveOrphanFilesJobContent` (one discriminated union, `MaintenanceJobContent`) hold the target file size, the cutoff time, the snapshots to keep and the policy's options, by their domain names. A compaction's partitions are `SpecPartitions`: a partition spec and the partition values selected under it, in Iceberg's internal form. `build_maintenance_job_content` resolves a policy, the table's properties and the time into content, and `group_partitions_by_spec` checks the selection the way the old builder did, without writing any text.
- **The run stores that content.** `TableMaintenanceRun.content` replaces `filters` and `procedure_args`, and a run refuses content of another operation. The plan, the Temporal payloads and the database (`content_json`) carry it as primitives.
- **The submit port takes a typed job.** `SubmitMaintenanceJobGatewayInput.job` is one of four primitive-only frozen dataclasses (`RewriteDataFilesJob` and the others, with `JobPartitionSpec` and `JobPartitionField`), built from the run's content by `gateway_job_of`.
- **Only the Spark adapter writes Iceberg's spelling.** `iceberg_procedure_args` writes the option names, which values go in the `options` map and the cutoff as UTC ISO text; `spark_where_clauses` and `spark_partition_where` write the `where` Spark SQL, with ADR 0004's escaping. `GLAC_REQUEST`, the request the Spark runtime reads, keeps its keys, order and values; a golden test pins it for fifteen planning inputs.

The web adapter writes a run's content for people: settings by their domain names, and partition values as Iceberg prints them (`2026-11-20` for a day). `tests/architecture/test_no_engine_spelling_in_application.py` fails when `application/` holds an Iceberg option name, Spark SQL, a time written as text or a `procedure_*` function.

## Consequences

- Adding an option is a field on the domain options and its spelling in `iceberg_procedure_args`; a parity test fails when one side has a field the other lacks.
- A run's record, in the API and the console, shows the settings and partitions a job used rather than the call's text, with no less information.
- The Spark runtime and the `CALL`s it runs are unchanged. A partition value no `where` can name still makes the plan compact the whole table, with the same warning.
- Stored runs are not migrated: `content_json` replaces two columns, so an existing database is rebuilt (KCL-110).

## References

- ADR 0004, Backslash escaping for Spark SQL string literals.
- ADR 0012, Policies on the catalog hierarchy (the `options` decision).
- Apache Iceberg, Spark procedures: https://iceberg.apache.org/docs/latest/spark-procedures/
