# 17. One image, a subcommand and a settings file per role

Date: 2026-11-25

Status: Accepted; the chart values amended 2026-11-25 (KCL-114, see Amendment).

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

## Amendment: the chart values follow open-source practice (2026-11-25, KCL-114)

The chart had to deploy to any cluster that has the external services, as Sentry's, Bitnami's and Trino's charts do, and a values file of a few knobs plus a `config:` pass-through in the backend's own names could not say which values an environment must give. Three decisions above change; the subcommands, the precedence and the per-role files stand.

- **`values.yaml` holds every generic setting with its value, grouped by meaning, and leaves every environment value empty.** The blocks are `global`, `external` (six services, each with a `type` that accepts one value: `postgresql`, `temporal`, `polaris`, `s3`, `kafka`, `prometheus`), `backend` (the image, the log level and the four roles), `frontend` (the console) and `maintenance` (discovery, cooldowns, back-off, partition selection and the Spark jobs). An environment is an overlay file (`values/minikube.yaml` here); without one the chart refuses to render, naming the value it misses.
- **The chart writes every setting a role reads into its file**, not only those set. The defaults are therefore in two places again, and a backend test (`tests/bootstrap/configs/test_chart_settings.py`) keeps them equal: each role loads the file written for it, every setting it reads has a key there, and every generic value equals the Pydantic default. Pydantic stays the reference.
- **`config:` and `<role>.config:` are gone**, and so are `enabled` and `settingsProfile`: every role always deploys. Maintenance, discovery and Spark stay shared, now because they have no per-role place; the chart refuses them in one role's `env`.

**A value the chart offers is one the component honours.** The API listens on `http.port` (default 8000), which the chart writes from `backend.api.port`, and the console's nginx on `CONSOLE_PORT` (default 8080) from `frontend.console.port`; both used to be fixed, so the values moved the Services and probes away from the process. The constants the templates held (probes, the migration's retries, the grace periods, the test pod's resources) are values too, and drift tests keep the defaults on what the API and the console build serve.

An existing deployment moves its overrides to the named values (`config.maintenance.compaction_quiet_seconds` becomes `maintenance.partitionSelection.quietSeconds`) and its addresses to an environment file; the schema refuses the old keys. The database Secret holds the `username` beside the `password`.

## References

- Thanos, components as subcommands of one binary: https://thanos.io/tip/thanos/getting-started.md/
- Trino Helm chart, per-role ConfigMaps: https://github.com/trinodb/charts
- Sentry Helm chart, external services by kind: https://github.com/sentry-kubernetes/charts
- Bitnami charts, `externalDatabase` and `existingSecret`: https://github.com/bitnami/charts
- pydantic-settings, CLI and YAML sources: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- ADR 0005, Bounded contexts (the composition root in `bootstrap/`).
