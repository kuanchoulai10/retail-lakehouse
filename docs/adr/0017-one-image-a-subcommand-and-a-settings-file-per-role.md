# 17. One image, a subcommand and a settings file per role

Date: 2026-11-25

Status: Accepted.

## Context

The backend runs as four roles from one image: the API, the Temporal worker, the Polaris event consumer and the schema migration. Until now `entrypoint.py` picked the role from `GLAC_COMPONENT`, and every role read one `AppSettings` from `GLAC_*` environment variables, which the chart rendered into one ConfigMap, `table-maintenance-config`, for all four pods. Each role was given every setting, including ones it never reads; a misspelt variable was silently ignored, so a value someone meant to set ran at its default; changing any setting restarted every pod, because they shared one checksum; and the defaults lived twice, in `values.yaml` and in Pydantic, so they could drift. The services also waited for the schema with a `psql` init container that named a table and a seeded policy id, so the chart knew the database's layout.

Linear KCL-113 asked for each role to read only its own settings, from a file, with unknown names refused at startup, and for the chart to follow how mature charts lay out per-role configuration.

## Decision

- **A role is a subcommand.** `glac api|worker|event-consumer|migrate`, as Thanos runs `thanos query|store|compact` from one binary. The image's entrypoint is `python -m bootstrap.cli`, and the installed package also gives a `glac` script. `glac migrate --wait` waits until the schema is migrated and seeded instead of migrating, and replaces the `psql` init container: the services wait through the backend, so no table name or seed id lives in the chart.
- **A role has a settings class.** `ApiSettings` and `WorkerSettings` extend `ServiceSettings` (database, Temporal, catalog, Spark, maintenance, discovery, metrics); the API adds `http`, the worker `callback_base_url`. `EventConsumerSettings` takes database, Temporal, catalog and Kafka, and `MigrateSettings` the database alone. Each block is a `SettingsBlock`.
- **Precedence is CLI, then environment, then the file, then the defaults.** `--config-file` names a YAML file; `GLAC_*` variables with `__` nesting carry the secrets (`GLAC_DATABASE__POSTGRES__DB_URL`, `GLAC_CATALOG__CREDENTIAL`); any setting is also a kebab-case flag.
- **An unknown name fails startup, naming it.** A key in the file or a `GLAC_*` variable the role does not take, a missing file, a file that is not a mapping, and a secret written in the file each stop the role before it connects to anything, with the name to fix. `glac <role>` prints the error and exits 2.
- **The chart renders one ConfigMap per role**, as the Trino chart renders one per coordinator and worker: `<fullname>-<role>-config`, holding `config.yaml`, mounted at `/etc/glac`. A role's file is the chart's own wiring (names that follow the release), the typed knobs, `config:` and `<role>.config:`, deep-merged in that order and cut to the keys the role takes. Each Deployment's checksum covers its own file, so a change restarts only the roles that read it.
- **Defaults live only in Pydantic.** `values.yaml` keeps a few typed knobs (`logLevel`, `maintenance.attemptDeadlineSeconds`, `maintenance.maxAttempts`, `maintenance.queueWaitLimitSeconds`, `spark.sizes`), each written only when set; everything else passes through `config:` in the settings' own names.
- **Maintenance, discovery and Spark are set for every role or none.** The platform settings page is served by the API and describes what the worker runs, so `<role>.config.maintenance`, `.discovery` and `.spark` fail before install, as do a `config:` key no role takes and a `<role>.config:` key that role does not take.

## Consequences

- A misspelt setting now stops a pod at startup instead of running a default nobody chose. A deployment that set a variable no role reads has to remove it.
- A setting change restarts only the roles whose file changed: a shared block the API and the worker both read restarts both, and not the event consumer.
- The API and the worker share `ServiceSettings` because they share the use-case wiring (`build_connected_use_cases`): the API plans what the worker runs and shows the worker's limits on the platform settings page. The cost is that the API is given the Spark and maintenance blocks it reads only to describe them.
- The e2e stays a black box: it reads the worker's mounted file as plain YAML to compare the platform settings page with what the worker was given, and takes the service addresses from its own `E2E_*` variables.
- An existing deployment moves its `values.yaml` overrides to `config:` under the settings' names (`worker.compactionQuietSeconds` becomes `config.maintenance.compaction_quiet_seconds`); the schema refuses the old keys.

## References

- Thanos, components as subcommands of one binary: https://thanos.io/tip/thanos/getting-started.md/
- Trino Helm chart, per-role ConfigMaps: https://github.com/trinodb/charts
- pydantic-settings, CLI and YAML sources: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- ADR 0005, Bounded contexts (the composition root in `bootstrap/`).
