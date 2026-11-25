# Table maintenance chart on open-source chart conventions, with chart tests (KCL-112) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The wave-25 chart can be adjusted through values alone, written the way the Trino chart (`trinodb/charts` 1.45.0) writes its own. PostgreSQL moves to a wave of its own. The chart has tests that fail locally when a template renders wrong.

**Architecture:**

- **Names and images.** Every name comes from a small set of helpers in `_helpers.tpl`: `fullname`, a name helper for each role, `labels`, `selectorLabels` and `image`. Each role keeps one template file and one values block.
- **Passing-through.** The chart gets two layers of pass-through fields: global `env`, `envFrom`, `secretMounts`, `commonLabels` and `extraManifests`, plus the same fields on each role.
- **Refusing bad values.** A `validateValues` helper refuses contradictory values with `fail`, and `values.schema.json` refuses unknown keys and wrong types.
- **The database.** It becomes `platform/20-table-maintenance-db`, plain manifests like `20-temporal-db`, and the chart only connects to it.
- **Tests.** There are three kinds:
  - helm-unittest suites in `chart/tests/`;
  - scenario values in `chart/ci/`, each rendered and label-checked;
  - a `helm test` Pod that calls the API's health check.

**Tech Stack:** Helm 4.1, helm-unittest v1.2.1 (Helm plugin), Task, bash, pytest for `scripts/tests`.

**Spec:** Linear KCL-112 ("Table maintenance 的 Helm chart 照開源 chart 的慣例整理，並補上 chart 測試"). There is no spec file: the issue's sections are the authority, and the rulings below settle what it leaves open.

## Global Constraints

### Scope

- Settings still travel as environment variables in this issue. KCL-113 replaces them with a settings file per role, so do not restructure `configmap.yaml` keys here.
- With release `table-maintenance`, the API, worker, event consumer, migrate Job, ConfigMap, database Service and worker ServiceAccount keep today's names. Only the console's names change: `console` becomes `table-maintenance-console`.

### Labels

- Selectors use only `app.kubernetes.io/name`, `app.kubernetes.io/instance` and `app.kubernetes.io/component`.
- Every Pod template carries `app.kubernetes.io/version`.
- `helm.sh/chart` goes on every object and never into a selector.
- These rules are in `platform/CLAUDE.md` under "Kubernetes labels" and are enforced by `scripts/check_k8s_labels.py`.

### Secrets

- `bootstrap.sh` still creates every Secret. The chart only refers to Secrets and never creates one that holds a password.

### Data

- Moving the database out of the release deletes the old PVC on `helm upgrade`. The data loss is accepted. Verification rebuilds the cluster (`task offboard` + `task onboard`, `KUBE_CONTEXT=retail-lakehouse`).

### helm-unittest

- Pinned at `v1.2.1`.
- Installed from the signed release tarball and verified against the project's `public-key.asc` (fingerprint `853008CD0B0A5A2DA04FF8A5616AD47F65B54AC7`), never with `--verify=false`. The Taskfile checks that it is there and at that version, and on a mismatch it fails and prints the install steps (Task 1 Step 1). It does not install the plugin itself.

### Hands off and shell rules

- Don't touch: the ArgoCD path (`bootstrap-by-argocd` in `tasks/apps.yml`, `platform/0[0-2]-*`), `platform/30-thanos`, `platform/24-e2e-validation`.
- Shell rules from the root `CLAUDE.md` apply:
  - no `cd`;
  - `uv run`;
  - `KUBE_CONTEXT=retail-lakehouse`;
  - `kubectl <verb>` first.
- No explanatory comment blocks in `values.yaml` or other infra config.

## Review Focus

- **A release named something else, or with `fullnameOverride`.** Every cross-reference must follow the new name; a hard-coded name anywhere is a bug. The references are: the ConfigMap's `GLAC_CALLBACK_BASE_URL`, the HTTPRoute `backendRefs`, the RoleBinding subjects, the ServiceAccount the worker uses, the Spark ServiceAccount the worker submits with, the Volcano queue and PriorityClass names, and `checksum/config`. Tests: Task 1's rename suite and Task 3's Volcano names.
- **A role turned off.** Nothing else may still refer to it. A console without the API, or a worker without the API (Spark result callbacks go to the API), fails before install with a message that says which value to change. Tests: Task 3's validation suite.
- **An unknown or misspelt key** (`worker.replica`, `api.resource`). It is refused by the schema and names the key. Tests: Task 3's schema cases.
- **Pass-through at both layers at once.** Global and role `env` on one pod must keep both lists, global first, so the role's entry wins when names collide. `secretMounts` must produce a volume and a mount whose names don't collide between the two layers. Tests: Task 2's pass-through suite.
- **The schema wait without the migrate Job.** With `migrate.enabled: false`, the init container still waits on the external database's seed rows. The pods must still render and must not refer to a migrate Job. Tests: Task 4's database suite.

---

## File Structure

| Path | Responsibility |
|---|---|
| `platform/25-lakehouse-control-plane/chart/Chart.yaml` | description without PostgreSQL |
| `chart/values.yaml` | the new values layout (see Task 1-4) |
| `chart/values.schema.json` | types and `additionalProperties: false` for the top level and each block |
| `chart/.helmignore` | `tests/`, `ci/` |
| `chart/templates/_helpers.tpl` | name, fullname, chart, per-role names, labels, selectorLabels, image, pod helpers |
| `chart/templates/validate.yaml` | `{{ include "table-maintenance.validateValues" . }}` only |
| `chart/templates/{api,worker,event-consumer,migrate-job,console,configmap,rbac,volcano}.yaml` | one role or concern each, on the helpers |
| `chart/templates/extra-manifests.yaml` | renders `extraManifests` with `tpl` |
| `chart/templates/tests/test-connection.yaml` | the `helm test` Pod |
| `chart/templates/postgres.yaml` | deleted |
| `chart/tests/{names,images,labels,roles,passthrough,volcano_rbac,validation,schema,database,test_connection}_test.yaml` | helm-unittest suites |
| `chart/ci/{default,renamed,minimal,external}-values.yaml` | scenario values |
| `platform/25-lakehouse-control-plane/Taskfile.yml` | component Taskfile: `unit-test` real, the other fixed names `TODO://` |
| `platform/20-table-maintenance-db/{bootstrap.sh,validate.sh,README.md,table-maintenance-db-{pvc,deployment,service}.yaml}` | the database wave |
| `platform/25-lakehouse-control-plane/{bootstrap.sh,validate.sh,README.md}` | no database secret or Deployment; `helm test`; console names |
| `tasks/apps.yml` | status, bootstrap, validate for the new wave |
| `tasks/gates/pre-pr/pre-pr.yml` | include `chart`, run `chart:unit-test` on the backend side |
| `scripts/check_k8s_labels.py` | render the chart once per `ci/*-values.yaml` |
| `scripts/tests/test_check_k8s_labels*.py`, `scripts/tests/test_control_plane_settings_profile.py` | follow the changes |
| `platform/CLAUDE.md`, wave 25 README, `docs/agents/project-history.md`, root `CLAUDE.md` Taskfile paragraph if the component list is named there | docs |

## Rulings made while planning (the user delegated decisions)

### Names and labels

- **Ruling: `app.kubernetes.io/name` is the chart name (`table-maintenance`) on every chart object, the console included.** The role is carried by `component` (`api`, `worker`, `event-consumer`, `migrate`, `ui`, `config`, `scheduling`, `spark-job`, `test`). This follows the Trino chart, where one name covers coordinator and worker. Cost if wrong: one selector value on the console.
- **Ruling: the Spark ServiceAccount, the Volcano queues and the PriorityClass prefix default to names built from the fullname.** They are `<fullname>-spark`, `<fullname>`, `<fullname>-urgent` and `<fullname>`, each overridable by a value, which defaults to `""`. With the default release they come out as today's names, and a second release does not collide on the cluster-scoped objects. Cost if wrong: none for the default release.

### Refusing bad values

- **Ruling: add `values.schema.json`.** The issue names silently accepted wrong values as a problem, and `fail` checks only what a template reads; a misspelt key is read by nobody. A JSON schema with `additionalProperties: false` is how open-source charts refuse unknown keys (Bitnami ships one). Cost if wrong: KCL-113 reshapes the schema along with the values.
- **Ruling: the contradictions refused with `fail`:**
  - `console.enabled` without `api.enabled` (the console proxies `/console/api` to the API);
  - `worker.enabled` without `api.enabled` (Spark result callbacks);
  - `eventConsumer.replicas` greater than 1 (it runs alone, `Recreate`, README "1 replica");
  - an empty `database.existingSecret` (the chart creates no password Secret);
  - `worker.serviceAccount.create: false` with an empty `worker.serviceAccount.name`;
  - `spark.serviceAccount.create: false` with an empty `spark.serviceAccount.name`.

  Each message names the value to change. Cost if wrong: one message loosened.

### Images and the database

- **Ruling: images keep one block per image** (`image.backend`, `image.spark`, `image.console`, each with `repository`, `tag`, `digest`), under the shared `image.registry` and `image.pullPolicy`. `--set image.backend.tag=…` in `bootstrap.sh`, `check_k8s_labels.py` and the scripts tests keeps working. Cost if wrong: none.
- **Ruling: `database.clientImage` (`postgres:17.11-alpine`)** stays in values for the two init containers, since the chart no longer ships the database image. The schema check's SQL and table names move into a helper no value reaches. Cost if wrong: none.

### Placing the checks

- **Ruling: `helm test` runs from wave 25's `validate.sh`,** after the rollouts. That way `task apps:validate` and the deploy run it. Cost if wrong: about 10 s per validate.
- **Ruling: the scenario values in `ci/` are label-checked by `scripts/check_k8s_labels.py` itself,** which renders the chart once per file in place of once, so the existing `k8s-labels` pre-commit hook enforces them. The component `unit-test` runs `helm lint` and `helm template` on each file. Cost if wrong: the hook takes about 1 s longer.

---

### Task 1: helm-unittest, the component Taskfile, and names, images and labels on helpers

**Files:**
- Create: `platform/25-lakehouse-control-plane/Taskfile.yml`, `chart/.helmignore`, `chart/tests/names_test.yaml`, `chart/tests/images_test.yaml`, `chart/tests/labels_test.yaml`
- Modify: `chart/templates/_helpers.tpl`, every file in `chart/templates/`, `chart/values.yaml`, `tasks/gates/pre-pr/pre-pr.yml`

**Interfaces:**
- Produces, in `_helpers.tpl`. The helpers that take a dict take `(dict "root" $ "component" "<role>")`:
  - `table-maintenance.name`: `.Chart.Name` or `nameOverride`, truncated to 63 characters and trimmed of `-`.
  - `table-maintenance.fullname`: Trino's algorithm. `fullnameOverride` if set; else the release name when it contains the name; else `<release>-<name>`. Truncated to 63.
  - `table-maintenance.chart`: `<name>-<version>` with `+` replaced by `_`.
  - Role names: `table-maintenance.api.fullname` gives `<fullname>-api`. Likewise `worker.fullname` (`-worker`), `eventConsumer.fullname` (`-event-consumer`), `migrate.fullname` (`-migrate`; the Job appends `-<revision>`), `console.fullname` (`-console`), `config.fullname` (`-config`), `spark.serviceAccountName` (`spark.serviceAccount.name`, or `<fullname>-spark`) and `worker.serviceAccountName` (`worker.serviceAccount.name`, or `<fullname>-worker`).
  - `table-maintenance.selectorLabels` (dict root component): `name`, `instance`, `component`.
  - `table-maintenance.labels` (dict root component, optional `version`): selectorLabels, `app.kubernetes.io/part-of: table-maintenance`, `version` when given, `managed-by`, `helm.sh/chart`, then `commonLabels`.
  - `table-maintenance.image` (dict root image), where `image` is one of `.Values.image.backend|spark|console`: `[<registry>/]<repository>:<tag or .Chart.AppVersion>[@<digest>]`.
  - `table-maintenance.imageTag` (dict root image): the effective tag, used as the `version` label.
- Produces in values:
  - `nameOverride: ""`, `fullnameOverride: ""`, `commonLabels: {}`;
  - `image.registry: ""`, and `image.<backend|spark|console>.{repository, tag: "", digest: ""}`.

- [ ] **Step 1: Check the plugin**

Run: `helm plugin list`
Expected: a `unittest` row at `1.2.1`, provenance `signed` (installed 2026-11-25). Otherwise install it with signature verification, in a keyring of its own:

1. Fetch `public-key.asc` at tag `v1.2.1` from `helm-unittest/helm-unittest`.
2. Run `gpg --dearmor` on it into a `pubring.gpg` in a scratch directory.
3. Run `helm plugin install https://github.com/helm-unittest/helm-unittest/releases/download/v1.2.1/unittest-1.2.1.tgz --keyring <that pubring.gpg>`.

- [ ] **Step 2: Write the component Taskfile**

- `unit-test` (`desc: "Run the wave-25 chart's helm-unittest suites and render its scenario values"`), in its own directory:
  1. Fail unless `helm plugin list` shows `unittest` at `1.2.1`. The message gives the install command above.
  2. `helm lint chart --set image.backend.tag=t --set image.spark.tag=t --set image.console.tag=t`.
  3. `helm unittest chart`.
  4. For each `chart/ci/*-values.yaml`: `helm lint chart --values <file>` and `helm template table-maintenance chart --namespace lakehouse-control-plane --values <file> >/dev/null`.
- `component-test`, `arch-test`, `security-test`, `coverage-test`, `integration-test` and `build-test` each echo `TODO://` with one line saying what each would do.
- In `tasks/gates/pre-pr/pre-pr.yml`:
  - include `chart` (`taskfile: ../../../platform/25-lakehouse-control-plane/Taskfile.yml`, `dir: ../../../platform/25-lakehouse-control-plane`, `internal: true`);
  - add `chart:unit-test` to `backend`'s `deps`;
  - extend its desc to name the chart.

- [ ] **Step 3: Write the failing suites**

`chart/tests/names_test.yaml`. Every test sets `image.backend.tag`, `image.spark.tag` and `image.console.tag` to `t`, and uses `release.name` and `release.namespace` as named:

- `default release keeps today's names`. Release `table-maintenance` gives these names:
  - Deployments `table-maintenance-api`, `-worker`, `-event-consumer`, `table-maintenance-console`;
  - Services `table-maintenance-api` and `table-maintenance-console`;
  - ConfigMap `table-maintenance-config`;
  - ServiceAccount `table-maintenance-worker`;
  - Job `table-maintenance-migrate-1`.
- `another release name renames everything and every reference`. Release `tm2`:
  - each name above becomes `tm2-table-maintenance-…`;
  - `GLAC_CALLBACK_BASE_URL` is `http://tm2-table-maintenance-api.<ns>.svc.cluster.local:8000`;
  - the API HTTPRoute `backendRefs[0].name` is `tm2-table-maintenance-api`;
  - the console HTTPRoute's is `tm2-table-maintenance-console`;
  - the worker Deployment's `serviceAccountName` is `tm2-table-maintenance-worker`;
  - the worker RoleBinding's `subjects[0].name` is `tm2-table-maintenance-worker`;
  - `GLAC_SPARK__SERVICE_ACCOUNT` is `tm2-table-maintenance-spark`;
  - each pod's `envFrom` `configMapRef` is `tm2-table-maintenance-config`.
- `fullnameOverride wins`. `fullnameOverride: tm` gives `tm-api`, `tm-worker`, `tm-config`.
- `nameOverride changes the name label`. `nameOverride: maint` gives `app.kubernetes.io/name: maint` on the API Deployment and its selector.

`chart/tests/images_test.yaml`:

- `tag empty uses appVersion`. With `image.backend.tag: ""`, the API container image is `table-maintenance-backend:0.1.0`.
- `registry and digest`. With `image.registry: reg.example`, `image.backend.tag: 1.2`, `image.backend.digest: sha256:abc`, the image is `reg.example/table-maintenance-backend:1.2@sha256:abc`.
- `spark image reaches the worker config`. `GLAC_SPARK__IMAGE` follows the same rule.
- `version label is the effective tag`. On the API pod template, `app.kubernetes.io/version` is `"1.2"`.

`chart/tests/labels_test.yaml`:

- `helm.sh/chart on every object, never in a selector`. On every template:
  - `metadata.labels["helm.sh/chart"]` matches `^table-maintenance-0\.1\.0$`;
  - Deployment `spec.selector.matchLabels` and Service `spec.selector` have exactly the keys `name`, `instance` and `component`.
- `commonLabels on every object and pod`. `commonLabels: {team: data}` puts `team: data` on the ConfigMap, the API Deployment and the API pod template, and not in the API selector.

- [ ] **Step 4: Run them to see them fail**

Run: `helm unittest platform/25-lakehouse-control-plane/chart`
Expected: FAIL. Names are hard-coded, `helm.sh/chart` is missing, and the image has no registry or appVersion fallback.

- [ ] **Step 5: Implement the helpers and move every template onto them**

- Replace each hard-coded name, image and label `dict` with the helpers above.
- `image.*.tag` is no longer `required`.
- The console's `name` label becomes the chart name, with component `ui`.

- [ ] **Step 6: Run them to see them pass, then check that nothing else broke**

Run: `task -d platform/25-lakehouse-control-plane unit-test`, `uv run --no-project --with pyyaml --with pytest pytest scripts/tests -q`, `uv run --no-project --with pyyaml python scripts/check_k8s_labels.py`
Expected: all pass. If `test_control_plane_settings_profile.py` reads a renamed object, update its lookup to the new helper name.

- [ ] **Step 7: Commit**

```bash
git add platform/25-lakehouse-control-plane/Taskfile.yml platform/25-lakehouse-control-plane/chart tasks/gates/pre-pr/pre-pr.yml scripts/tests
git commit -m "refactor(chart): names, images and labels come from helpers, with helm-unittest suites (KCL-112)"
```

### Task 2: One block per role, with the two layers of pass-through

**Files:**
- Create: `chart/templates/extra-manifests.yaml`, `chart/tests/roles_test.yaml`, `chart/tests/passthrough_test.yaml`
- Modify: `chart/values.yaml`, `chart/templates/{api,worker,event-consumer,migrate-job,console,rbac}.yaml`, `chart/templates/_helpers.tpl`

**Interfaces:**
- Consumes: Task 1's helpers.
- Produces, in values. Each of `api`, `worker`, `eventConsumer`, `migrate` and `console` has:
  - `enabled: true`;
  - `replicas: 1` (not on `migrate`);
  - `labels: {}` and `annotations: {}` (the workload's own);
  - `podLabels: {}` and `podAnnotations: {}`;
  - `nodeSelector: {}`, `tolerations: []`, `affinity: {}`;
  - `resources` (today's values);
  - `env: []`, `envFrom: []`, `secretMounts: []`.
- Produces, as global values: `env: []`, `envFrom: []`, `secretMounts: []`, `extraManifests: []`, `imagePullSecrets: []`.
- Produces `worker.serviceAccount: {create: true, name: "", annotations: {}}` and `spark.serviceAccount: {create: true, name: "", annotations: {}}`. `spark.serviceAccount` was a string; it becomes this block.
- Produces these helpers, each taking `(dict "root" $ "role" .Values.<role>)`:
  - `table-maintenance.extraEnv`: the global `env` then the role's;
  - `table-maintenance.extraEnvFrom`: likewise;
  - `table-maintenance.secretVolumes`: one volume per mount, named `secret-<global|role>-<name>`;
  - `table-maintenance.secretVolumeMounts`: `{name, mountPath: .path, readOnly: true}`;
  - `table-maintenance.podScheduling`: renders whichever of `nodeSelector`, `tolerations` and `affinity` are set, plus `imagePullSecrets`.
- A `secretMounts` entry is `{name, secretName, path}`, as in Trino.

- [ ] **Step 1: Write the failing suites**

`chart/tests/roles_test.yaml`:

- `each role turns off`:
  - `worker.enabled: false` renders no worker Deployment, ServiceAccount, Role or RoleBinding, and no Spark ServiceAccount, Role or RoleBinding.
  - `eventConsumer.enabled: false` renders no event-consumer Deployment.
  - `migrate.enabled: false` renders no Job.
  - `console.enabled: false` renders no console Deployment, Service or HTTPRoute.
  - `api.enabled: false`, with worker and console off, renders no API Deployment, Service or HTTPRoute.
- `replicas`. `api.replicas: 3` gives `spec.replicas: 3`.
- `scheduling`. `worker.nodeSelector: {pool: maint}`, `worker.tolerations: [{key: k, operator: Exists}]` and `worker.affinity: {nodeAffinity: {…}}` appear on the worker pod spec and on no other pod.
- `workload and pod labels and annotations`. `api.labels: {a: "1"}` lands on the Deployment's metadata only; `api.podLabels: {b: "2"}` on the pod template only, not in the selector; `api.podAnnotations: {c: "3"}` sits beside `checksum/config`.
- `serviceAccount`:
  - `worker.serviceAccount.create: false` with `name: existing-sa` renders no worker ServiceAccount, and the worker uses `existing-sa`;
  - `worker.serviceAccount.annotations` land on the ServiceAccount.

`chart/tests/passthrough_test.yaml`:

- `global and role env both reach the pod, global first`:
  - with `env: [{name: G, value: g}]` and `worker.env: [{name: W, value: w}]`, the worker container's env ends with `G` then `W`;
  - the API's env has `G` and not `W`.
- `role env comes after global, so it wins a name`. With `env: [{name: X, value: global}]` and `api.env: [{name: X, value: role}]`, the last `X` in the API env is `role`.
- `envFrom layers` work the same, after today's `configMapRef` and the S3 `secretRef`.
- `secretMounts at both layers`. `secretMounts: [{name: ca, secretName: ca-bundle, path: /etc/ca}]` plus `api.secretMounts: [{name: tls, secretName: api-tls, path: /etc/tls}]` give:
  - the API pod volumes `secret-global-ca` and `secret-role-tls`, and mounts at `/etc/ca` and `/etc/tls` with `readOnly: true`;
  - the worker only `secret-global-ca`.
- `extraManifests`. `extraManifests: ["apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {{ include \"table-maintenance.fullname\" . }}-extra"]` renders a ConfigMap named `table-maintenance-extra`.

- [ ] **Step 2: Run them to see them fail**

Run: `helm unittest platform/25-lakehouse-control-plane/chart`
Expected: the new suites FAIL; Task 1's pass.

- [ ] **Step 3: Implement the role blocks, the pass-through helpers and `extra-manifests.yaml`**

- Wrap each role's file in `{{- if .Values.<role>.enabled }}`.
- `rbac.yaml` splits its worker part (behind `worker.enabled` and `worker.serviceAccount.create`) from its Spark part (behind `worker.enabled` and `spark.serviceAccount.create`). Task 3 adds `rbac.create`.
- `extra-manifests.yaml` renders each entry with `tpl` (a string, or `toYaml` of an object) after a `---`.

- [ ] **Step 4: Run them to see them pass**

Run: `task -d platform/25-lakehouse-control-plane unit-test`, `uv run --no-project --with pyyaml --with pytest pytest scripts/tests -q`, `uv run --no-project --with pyyaml python scripts/check_k8s_labels.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add platform/25-lakehouse-control-plane/chart
git commit -m "feat(chart): one values block per role, scheduling and pass-through at two layers (KCL-112)"
```

### Task 3: Create switches for Volcano and RBAC, contradictory values refused, a values schema

**Files:**
- Create: `chart/templates/validate.yaml`, `chart/values.schema.json`, `chart/tests/volcano_rbac_test.yaml`, `chart/tests/validation_test.yaml`, `chart/tests/schema_test.yaml`
- Modify: `chart/values.yaml`, `chart/templates/{volcano,rbac,configmap}.yaml`, `chart/templates/_helpers.tpl`

**Interfaces:**
- Consumes: Tasks 1-2.
- Produces in values:
  - `volcano.create: true`;
  - `volcano.queues.maintenance.name: ""` and `volcano.queues.urgent.name: ""`;
  - `volcano.priorityClassPrefix: ""`;
  - `rbac.create: true`.
- Produces these helpers:
  - `table-maintenance.volcano.queue` and `table-maintenance.volcano.urgentQueue` give `<fullname>` and `<fullname>-urgent` when the value is empty;
  - `table-maintenance.volcano.priorityClassPrefix` gives `<fullname>` when empty;
  - `table-maintenance.validateValues`.

- [ ] **Step 1: Write the failing suites**

`chart/tests/volcano_rbac_test.yaml`:

- `volcano.create false` renders no Queue and no PriorityClass, while `GLAC_SPARK__VOLCANO__QUEUE` is still set.
- `queue names follow the release`. Release `tm2` gives Queues `tm2-table-maintenance` and `tm2-table-maintenance-urgent`, PriorityClass `tm2-table-maintenance-p0`, and matching `GLAC_SPARK__VOLCANO__QUEUE`, `GLAC_SPARK__VOLCANO__URGENT_QUEUE` and `GLAC_SPARK__VOLCANO__PRIORITY_CLASS_PREFIX`.
- `default release keeps today's Volcano names`: `table-maintenance`, `table-maintenance-urgent`, `table-maintenance-p3`.
- `rbac.create false` renders no Role and no RoleBinding in either namespace, and still renders the ServiceAccounts.

`chart/tests/validation_test.yaml`. Each case asserts `failedTemplate.errorMessage` contains the text given:

- `console without the API` contains `console.enabled needs api.enabled: the console sends /console/api to the API`.
- `worker without the API` contains `worker.enabled needs api.enabled: Spark jobs send their results to the API`.
- `event consumer replicas` (`eventConsumer.replicas: 2`) contains `eventConsumer.replicas must be 0 or 1: Polaris events are consumed by one consumer`.
- `no database secret` (`database.existingSecret: ""`) contains `database.existingSecret is required: the chart creates no password Secret; bootstrap.sh of platform/20-table-maintenance-db does`. Task 4 adds `database`; this case is written in Task 4 and listed here for the message.
- `worker serviceAccount without a name` (`create: false`, `name: ""`) contains `worker.serviceAccount.name is required when worker.serviceAccount.create is false`.
- The same for `spark.serviceAccount`.

`chart/tests/schema_test.yaml`. Each case asserts `failedTemplate` with an error that names the key:

- `unknown top-level key` (`replica: 2`);
- `unknown role key` (`worker.replica: 2`);
- `wrong type` (`api.replicas: "two"`);
- `unknown image key` (`image.backend.tags: x`).

- [ ] **Step 2: Run them to see them fail**

Run: `helm unittest platform/25-lakehouse-control-plane/chart`
Expected: the new suites FAIL.

- [ ] **Step 3: Implement**

- Put the `volcano.create` and `rbac.create` guards in.
- Add the Volcano name helpers, used by `volcano.yaml` and `configmap.yaml`.
- `validateValues` holds the `fail` cases in the order above and is included from `templates/validate.yaml`.
- `values.schema.json` uses draft-07, with `additionalProperties: false` on:
  - the top level;
  - `image` and each image;
  - each role block;
  - `worker.serviceAccount`, `spark.serviceAccount`, `volcano`, `rbac`;
  - and later `database`.

  It types `enabled` (boolean), `replicas` (integer ≥ 0), `env` (array), `secretMounts` (an array of `{name, secretName, path}`, all required strings). Free-form maps (`labels`, `annotations`, `nodeSelector`, `affinity`, `resources`, `commonLabels`) are `type: object` with no further constraint.

- [ ] **Step 4: Run them to see them pass**

Run: `task -d platform/25-lakehouse-control-plane unit-test`, then `helm template table-maintenance platform/25-lakehouse-control-plane/chart --values platform/25-lakehouse-control-plane/chart/values-e2e.yaml --set image.backend.tag=t --set image.spark.tag=t --set image.console.tag=t >/dev/null`
Expected: PASS; the e2e overlay passes the schema.

- [ ] **Step 5: Commit**

```bash
git add platform/25-lakehouse-control-plane/chart
git commit -m "feat(chart): switches for Volcano and RBAC, contradictory and unknown values refused before install (KCL-112)"
```

### Task 4: PostgreSQL in a wave of its own, the chart only connects to it

**Files:**
- Create:
  - `platform/20-table-maintenance-db/bootstrap.sh`, `validate.sh`, `README.md`;
  - `platform/20-table-maintenance-db/table-maintenance-db-pvc.yaml`, `table-maintenance-db-deployment.yaml`, `table-maintenance-db-service.yaml`;
  - `chart/tests/database_test.yaml`.
- Delete: `chart/templates/postgres.yaml`
- Modify:
  - `chart/values.yaml` and `values.schema.json`, where `postgres:` becomes `database:`;
  - `chart/templates/_helpers.tpl` (`dbEnv`, `waitForSchema`, migrate's wait);
  - `chart/templates/migrate-job.yaml`, `chart/Chart.yaml`;
  - `platform/25-lakehouse-control-plane/bootstrap.sh` (the database Secret block moves out) and `validate.sh` (no `table-maintenance-db` rollout);
  - `tasks/apps.yml`.

**Interfaces:**
- Produces in values: `database: {host: table-maintenance-db, port: 5432, name: table_maintenance, user: table_maintenance, existingSecret: table-maintenance-db, secretKey: password, clientImage: postgres:17.11-alpine}`.
- Produces helpers:
  - `table-maintenance.dbEnv`: `DB_PASSWORD` from `existingSecret`/`secretKey`, and `GLAC_POSTGRES__DB_URL` = `postgresql+psycopg://<user>:$(DB_PASSWORD)@<host>:<port>/<name>`;
  - `table-maintenance.waitForSchema`, which keeps today's query and is reached by no value;
  - `table-maintenance.waitForDatabase` (`pg_isready -h <host> -p <port>`).
- Produces the wave: `namespace::apply_ambient lakehouse-control-plane`. If the Secret `table-maintenance-db` is missing, it is created with key `password` (`openssl rand -hex 24`), moved verbatim from wave 25's `bootstrap.sh`. Then the PVC (5Gi), the Deployment (`Recreate`, today's probes and `PGDATA`) and the Service `table-maintenance-db:5432` are applied.
  - Labels: `name: postgres`, `instance: table-maintenance-db`, `component: database`, `part-of: table-maintenance`, `managed-by: kubectl`; the pod adds `version: "17.11-alpine"`.
  - `validate.sh` asserts the namespace is ambient, the rollout succeeds, and `pg_isready -U table_maintenance -d table_maintenance` passes, selecting the pod by `name=postgres,instance=table-maintenance-db`.

- [ ] **Step 1: Write the failing suite**

`chart/tests/database_test.yaml`:

- `no database objects in the chart`. No template renders a PVC, a Deployment with component `database`, or a Service named `table-maintenance-db`.
- `URL from values`. With `database: {host: pg.example, port: 6543, name: tm, user: u, existingSecret: s, secretKey: k}`:
  - every app container (api, worker, event-consumer, migrate) has `GLAC_POSTGRES__DB_URL` = `postgresql+psycopg://u:$(DB_PASSWORD)@pg.example:6543/tm`;
  - `DB_PASSWORD` comes from secret `s`, key `k`.
- `schema wait points at the database and needs no migrate Job`. With `migrate.enabled: false`:
  - the API pod's `wait-for-schema` init container uses `database.clientImage`, and its command holds `-h pg.example -p 6543`;
  - no Job renders.
- `migrate waits for the database host`. The migrate Job's init command is `pg_isready -h pg.example -p 6543 …`.
- Add the `no database secret` case to `validation_test.yaml` (Task 3's message).

- [ ] **Step 2: Run it to see it fail**

Run: `helm unittest platform/25-lakehouse-control-plane/chart`
Expected: FAIL. `postgres.yaml` still renders, the URL host is fixed, and there is no `database` key in the schema.

- [ ] **Step 3: Implement the chart side**

- Delete `postgres.yaml`.
- Replace `postgres:` with `database:` in values and schema.
- Rewrite the three helpers.
- `Chart.yaml` `description: Iceberg table maintenance control plane (API, Temporal worker, event consumer, migrate Job, console)`.

- [ ] **Step 4: Run it to see it pass**

Run: `task -d platform/25-lakehouse-control-plane unit-test`
Expected: PASS.

- [ ] **Step 5: Create the wave and wire it**

- Write the four manifests and both scripts as in Interfaces, using `20-temporal-db` as the pattern. The PVC name `table-maintenance-db` stays.
- Remove the database Secret block from wave 25's `bootstrap.sh`, and `table-maintenance-db` from `validate.sh`'s rollout loop.
- In `tasks/apps.yml`:
  - add `TIMEOUT=10s bash platform/20-table-maintenance-db/validate.sh` to `bootstrap`'s `status`, after `20-temporal-db`;
  - add `bash platform/20-table-maintenance-db/bootstrap.sh` and `validate.sh` to `bootstrap`'s `cmds`, after `20-temporal-db`'s;
  - add an internal task `validate-table-maintenance-db`, and call it from `validate` before `validate-lakehouse-control-plane`.
  - Leave `bootstrap-by-argocd` alone.
- The README follows `20-temporal-db/README.md`'s structure: what it is, what creates the Secret, and that the data is lost when the wave is deleted.

- [ ] **Step 6: Check the manifests**

Run: `uv run --no-project --with pyyaml python scripts/check_k8s_labels.py`, `shellcheck platform/20-table-maintenance-db/*.sh platform/25-lakehouse-control-plane/*.sh`, `uv run --no-project --with pyyaml --with pytest pytest scripts/tests -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add platform/20-table-maintenance-db platform/25-lakehouse-control-plane tasks/apps.yml
git commit -m "feat(platform): PostgreSQL for table maintenance is a wave of its own; the chart only connects to it (KCL-112)"
```

### Task 5: Scenario values, the label check over them, and `helm test`

**Files:**
- Create:
  - `chart/ci/default-values.yaml` (image tags only);
  - `chart/ci/renamed-values.yaml` (`fullnameOverride: tm-ci`, `nameOverride: maint`, `commonLabels`);
  - `chart/ci/minimal-values.yaml` (api and migrate only: worker, eventConsumer and console off; `volcano.create: false`);
  - `chart/ci/external-values.yaml`:
    - `rbac.create: false`;
    - worker and Spark ServiceAccounts with `create: false` and names given;
    - an external `database`;
    - a registry and a digest;
    - global and role `env`, `secretMounts` and `extraManifests`;
    - scheduling settings on every role.
  - `chart/templates/tests/test-connection.yaml`, `chart/tests/test_connection_test.yaml`.
- Modify: `scripts/check_k8s_labels.py`, `scripts/tests/test_check_k8s_labels*.py` (whichever file tests `rendered_chart`), `platform/25-lakehouse-control-plane/validate.sh`

**Interfaces:**
- Consumes: Tasks 1-4's values.
- Produces:
  - `check_k8s_labels.rendered_chart(root) -> list[tuple[str, str]]`: `(source label, rendered text)` for each `chart/ci/*-values.yaml`, sorted, each rendered with `--values <file>` on top of the three `--set image.*.tag=check`. `main` extends `sources` with them.
  - The test Pod `<fullname>-test-connection`:
    - annotations `helm.sh/hook: test` and `helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded`;
    - component `test` and the version label;
    - the backend image, `restartPolicy: Never`, `automountServiceAccountToken: false`, and the chart's pod and container security;
    - command `["python", "-c", "import urllib.request; urllib.request.urlopen('http://<api fullname>:<port>/healthz', timeout=10)"]`;
    - rendered only when `api.enabled`.

- [ ] **Step 1: Write the failing tests**

`chart/tests/test_connection_test.yaml`:

- `test pod calls the API health check`. `metadata.annotations["helm.sh/hook"]` is `test`, and the command contains `http://table-maintenance-api:8000/healthz`.
- `renamed release`. With release `tm2`, the URL is `http://tm2-table-maintenance-api:8000/healthz`.
- `no test pod without the API`. With api, worker and console off, nothing renders.

In the scripts test for the label checker, add these two tests:

- `test_rendered_chart_renders_each_ci_values_file`. `rendered_chart(ROOT)` returns one entry per `chart/ci/*-values.yaml`. Each label names its file, and each text contains `kind: Deployment` (or, for minimal, the API Deployment).
- `test_every_ci_scenario_passes_the_label_check`. For each rendered text, `check_document` yields no violation.

- [ ] **Step 2: Run them to see them fail**

Run: `helm unittest platform/25-lakehouse-control-plane/chart` and `uv run --no-project --with pyyaml --with pytest pytest scripts/tests -q`
Expected: FAIL. There is no test Pod, and `rendered_chart` returns a string.

- [ ] **Step 3: Implement**

- Write the `ci/` files, the test Pod and the new `rendered_chart`.
- In wave 25's `validate.sh`, after the rollouts and the migrate Job wait: `helm test table-maintenance --namespace lakehouse-control-plane --kube-context "${KUBE_CONTEXT}" --timeout "${HELM_TEST_TIMEOUT:-120s}"`. It has its own timeout because `tasks/apps.yml` runs `validate.sh` as a `status` check with `TIMEOUT=10s`. Starting a Pod can take longer than 10 s, and a failed status check re-runs the whole bootstrap.
- Also in `validate.sh`, change the rollout loop's `console` to `table-maintenance-console`, and `gateway::assert_route_accepted "${NAMESPACE}" console` to `table-maintenance-console`.

- [ ] **Step 4: Run them to see them pass**

Run: `task -d platform/25-lakehouse-control-plane unit-test`, `uv run --no-project --with pyyaml --with pytest pytest scripts/tests -q`, `uv run --no-project --with pyyaml python scripts/check_k8s_labels.py`, `shellcheck platform/25-lakehouse-control-plane/validate.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add platform/25-lakehouse-control-plane scripts
git commit -m "test(chart): scenario values pass the label check and helm test calls the API (KCL-112)"
```

### Task 6: Rebuild, verify on the cluster, docs

**Files:**
- Modify:
  - `platform/CLAUDE.md` (the wave list gains `20-table-maintenance-db`; the label rules mention `helm.sh/chart`);
  - the wave 25 README (deployed resources without PostgreSQL, the values layout, the tests and how to run them, the console's new names);
  - the root `CLAUDE.md`'s Taskfile paragraph, only if it lists the components a gate includes (it names `backend`, `spark` for the backend side: add the chart);
  - `docs/agents/project-history.md`.

- [ ] **Step 1: Rebuild the cluster**

Run: `task offboard KUBE_CONTEXT=retail-lakehouse`, then `task onboard KUBE_CONTEXT=retail-lakehouse`. Then `task apps:bootstrap KUBE_CONTEXT=retail-lakehouse`, if onboard does not bootstrap the apps (check `Taskfile.yml`).
Expected: every wave validates, `20-table-maintenance-db` before 25.

- [ ] **Step 2: Validate wave 25 and run the critical e2e**

Run: `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/validate.sh`, then `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e/run.sh critical`
Expected: `validate.sh` passes with `helm test` green, and critical is 31/31.

- [ ] **Step 3: Check the console through the gateway**

Run: the console paths in `validate.sh` (step 2 covers them).
Expected: `/console/` answers through `table-maintenance-console`.

- [ ] **Step 4: Docs, then the gate and the commit together**

Run: `task gates:pre-pr && git add platform/CLAUDE.md platform/25-lakehouse-control-plane/README.md platform/20-table-maintenance-db/README.md CLAUDE.md docs/agents/project-history.md && git commit -m "docs(chart): the chart's values, tests and the database wave (KCL-112)"`
Expected: the gate passes, including `chart:unit-test`, and the commit lands.
