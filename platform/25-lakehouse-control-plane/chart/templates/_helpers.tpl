{{- define "table-maintenance.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "table-maintenance.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "table-maintenance.suffixed" -}}
{{- printf "%s-%s" (include "table-maintenance.fullname" .root) .suffix | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "table-maintenance.api.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "api") }}
{{- end -}}

{{- define "table-maintenance.worker.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "worker") }}
{{- end -}}

{{- define "table-maintenance.eventConsumer.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "event-consumer") }}
{{- end -}}

{{- define "table-maintenance.migrate.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "migrate") }}
{{- end -}}

{{- define "table-maintenance.console.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "console") }}
{{- end -}}

{{- define "table-maintenance.backendRoles" -}}
api worker eventConsumer migrate
{{- end -}}

{{- define "table-maintenance.roleSuffix" -}}
{{- get (dict "api" "api" "worker" "worker" "eventConsumer" "event-consumer" "migrate" "migrate") . }}
{{- end -}}

{{- define "table-maintenance.roleConfig.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" .root "suffix" (printf "%s-config" (include "table-maintenance.roleSuffix" .role))) }}
{{- end -}}

{{- define "table-maintenance.role" -}}
{{- toYaml (get .root.Values.backend .role) }}
{{- end -}}

{{- define "table-maintenance.roleKeys" -}}
{{- $service := list "log_level" "database" "temporal" "catalog" "spark" "maintenance" "discovery" "metrics" }}
{{- $keys := dict
  "api" (append $service "http")
  "worker" (append $service "callback_base_url")
  "eventConsumer" (list "log_level" "database" "temporal" "catalog" "kafka")
  "migrate" (list "log_level" "database") }}
{{- get $keys . | join " " }}
{{- end -}}

{{- define "table-maintenance.sharedOnlyKeys" -}}
maintenance discovery spark
{{- end -}}

{{- define "table-maintenance.size" -}}
{{- toYaml (dict "driver_memory" .driverMemory "executor_memory" .executorMemory "executor_instances" .executorInstances) }}
{{- end -}}

{{- define "table-maintenance.settings" -}}
{{- $external := .Values.external }}
{{- $polaris := trimSuffix "/" $external.catalog.polaris.endpoint }}
{{- $s3 := $external.objectStorage.s3 }}
{{- $maintenance := .Values.maintenance }}
{{- $jobs := $maintenance.jobs }}
{{- $settings := dict
  "database" (dict "backend" "postgres" "postgres" (dict "pool_size" $external.database.postgresql.poolSize))
  "temporal" (dict "address" $external.orchestrator.temporal.endpoint "namespace" $external.orchestrator.temporal.namespace)
  "catalog" (dict
    "uri" (printf "%s/api/catalog" $polaris)
    "management_uri" (printf "%s/api/management/v1" $polaris)
    "scope" $external.catalog.polaris.scope
    "s3_endpoint" $s3.endpoint
    "s3_path_style_access" $s3.pathStyleAccess
    "s3_region" $s3.region)
  "kafka" (dict "bootstrap_servers" $external.catalogEvents.kafka.endpoint "topic" $external.catalogEvents.kafka.topic)
  "metrics" (dict
    "prometheus_url" $external.metricsHistory.prometheus.endpoint
    "query_timeout_seconds" $external.metricsHistory.prometheus.queryTimeoutSeconds)
  "discovery" (dict "interval_seconds" $maintenance.discovery.intervalSeconds)
  "maintenance" (dict
    "attempt_deadline_seconds" $jobs.limits.attemptDeadlineSeconds
    "max_attempts" $jobs.limits.maxAttempts
    "queue_wait_limit_seconds" $jobs.limits.queueWaitLimitSeconds
    "failure_backoff_cap_seconds" $maintenance.failureBackoffCapSeconds
    "rewrite_data_files_cooldown_seconds" $maintenance.cooldowns.rewriteDataFilesSeconds
    "rewrite_manifests_cooldown_seconds" $maintenance.cooldowns.rewriteManifestsSeconds
    "expire_snapshots_cooldown_seconds" $maintenance.cooldowns.expireSnapshotsSeconds
    "remove_orphan_files_interval_seconds" $maintenance.cooldowns.removeOrphanFilesIntervalSeconds
    "compaction_partitions_per_job" $maintenance.partitionSelection.partitionsPerJob
    "compaction_quiet_seconds" $maintenance.partitionSelection.quietSeconds
    "compaction_max_quiet_wait_seconds" $maintenance.partitionSelection.maxQuietWaitSeconds)
  "spark" (dict
    "image" (include "table-maintenance.image" (dict "root" . "image" $jobs.image))
    "image_pull_policy" .Values.global.image.pullPolicy
    "service_account" (include "table-maintenance.spark.serviceAccountName" .)
    "catalog_credential_secret" $external.catalog.polaris.credentialsSecret
    "s3_secret_name" $s3.credentialsSecret
    "namespace" $jobs.namespace
    "spark_version" $jobs.spark.sparkVersion
    "iceberg_version" $jobs.spark.icebergVersion
    "hadoop_version" $jobs.spark.hadoopVersion
    "aws_sdk_version" $jobs.spark.awsSdkVersion
    "event_log_dir" $jobs.spark.eventLogDir
    "main_application_file" $jobs.spark.mainApplicationFile
    "driver_cores" $jobs.cores.driver
    "driver_core_limit" $jobs.cores.driverLimit
    "executor_cores" $jobs.cores.executor
    "executor_core_limit" $jobs.cores.executorLimit
    "size_s" (include "table-maintenance.size" $jobs.sizes.S | fromYaml)
    "size_m" (include "table-maintenance.size" $jobs.sizes.M | fromYaml)
    "size_l" (include "table-maintenance.size" $jobs.sizes.L | fromYaml)
    "volcano" (dict
      "queue" (include "table-maintenance.volcano.queue" .)
      "urgent_queue" (include "table-maintenance.volcano.urgentQueue" .)
      "priority_class_prefix" (include "table-maintenance.volcano.priorityClassPrefix" .)))
  "callback_base_url" (printf "http://%s.%s.svc.cluster.local:%v" (include "table-maintenance.api.fullname" .) .Release.Namespace .Values.backend.api.port)
  "http" (dict "root_path" .Values.backend.api.rootPath "port" (int .Values.backend.api.port)) }}
{{- toYaml $settings }}
{{- end -}}

{{- define "table-maintenance.roleConfig" -}}
{{- $settings := include "table-maintenance.settings" .root | fromYaml }}
{{- $_ := set $settings "log_level" ((get .root.Values.backend .role).logLevel | default .root.Values.backend.logLevel) }}
{{- $out := dict }}
{{- range splitList " " (include "table-maintenance.roleKeys" .role) }}
{{- $_ := set $out . (get $settings .) }}
{{- end }}
{{- toYaml $out }}
{{- end -}}

{{- define "table-maintenance.configFile" -}}
/etc/glac/config.yaml
{{- end -}}

{{- define "table-maintenance.roleArgs" -}}
- {{ include "table-maintenance.roleSuffix" .role }}
- --config-file={{ include "table-maintenance.configFile" . }}
{{- end -}}

{{- define "table-maintenance.configVolumeMount" -}}
- name: config
  mountPath: /etc/glac
  readOnly: true
{{- end -}}

{{- define "table-maintenance.configVolume" -}}
- name: config
  configMap:
    name: {{ include "table-maintenance.roleConfig.fullname" . }}
{{- end -}}

{{- define "table-maintenance.worker.serviceAccountName" -}}
{{- default (include "table-maintenance.worker.fullname" .) .Values.backend.worker.serviceAccount.name }}
{{- end -}}

{{- define "table-maintenance.spark.serviceAccountName" -}}
{{- default (include "table-maintenance.suffixed" (dict "root" . "suffix" "spark")) .Values.maintenance.jobs.serviceAccount.name }}
{{- end -}}

{{- define "table-maintenance.imageTag" -}}
{{- default .root.Chart.AppVersion .image.tag }}
{{- end -}}

{{- define "table-maintenance.image" -}}
{{- with .root.Values.global.image.registry }}{{ . }}/{{ end }}
{{- .image.repository }}:{{ include "table-maintenance.imageTag" . }}
{{- with .image.digest }}@{{ . }}{{ end }}
{{- end -}}

{{- define "table-maintenance.selectorLabels" -}}
app.kubernetes.io/name: {{ include "table-maintenance.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "table-maintenance.labels" -}}
{{ include "table-maintenance.selectorLabels" . }}
app.kubernetes.io/part-of: table-maintenance
{{- with .version }}
app.kubernetes.io/version: {{ . | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ include "table-maintenance.chart" .root }}
{{- with .root.Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.dbLogin" -}}
{{- $secret := .Values.external.database.postgresql.credentialsSecret -}}
- name: DB_USERNAME
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: username
{{- if not .userOnly }}
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: password
{{- end }}
{{- end -}}

{{- define "table-maintenance.dbEnv" -}}
{{- $postgresql := .Values.external.database.postgresql -}}
{{ include "table-maintenance.dbLogin" . }}
- name: GLAC_DATABASE__POSTGRES__DB_URL
  value: postgresql+psycopg://$(DB_USERNAME):$(DB_PASSWORD)@{{ $postgresql.endpoint }}/{{ $postgresql.database }}?sslmode={{ $postgresql.sslMode }}
{{- end -}}

{{- define "table-maintenance.appEnv" -}}
{{ include "table-maintenance.dbEnv" . }}
- name: GLAC_CATALOG__CREDENTIAL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.external.catalog.polaris.credentialsSecret }}
      key: credential
{{- end -}}

{{- define "table-maintenance.s3EnvFrom" -}}
- secretRef:
    name: {{ .Values.external.objectStorage.s3.credentialsSecret }}
{{- end -}}

{{- define "table-maintenance.waitForDatabase" -}}
{{- $postgresql := .Values.external.database.postgresql }}
{{- $hostPort := splitList ":" $postgresql.endpoint -}}
- name: wait-for-db
  image: {{ .Values.backend.migrate.waitForDatabase.image }}
  imagePullPolicy: IfNotPresent
  env:
    {{- include "table-maintenance.dbLogin" (merge (dict "userOnly" true) .) | nindent 4 }}
  command:
    - sh
    - -c
    - until pg_isready -h {{ first $hostPort }} -p {{ last $hostPort }} -U "$DB_USERNAME" -d {{ $postgresql.database }}; do sleep 2; done
  {{- include "table-maintenance.containerSecurity" . | nindent 2 }}
{{- end -}}

{{- define "table-maintenance.waitForSchema" -}}
- name: wait-for-schema
  image: {{ include "table-maintenance.image" (dict "root" . "image" .Values.backend.image) }}
  imagePullPolicy: {{ .Values.global.image.pullPolicy }}
  args:
    - migrate
    - --wait
    - --config-file={{ include "table-maintenance.configFile" . }}
  env:
    {{- include "table-maintenance.migrate.env" . | nindent 4 }}
  volumeMounts:
    - name: migrate-config
      mountPath: /etc/glac
      readOnly: true
  {{- include "table-maintenance.containerSecurity" . | nindent 2 }}
{{- end -}}

{{- define "table-maintenance.waitForSchemaVolume" -}}
- name: migrate-config
  configMap:
    name: {{ include "table-maintenance.roleConfig.fullname" (dict "root" . "role" "migrate") }}
{{- end -}}

{{- define "table-maintenance.podSecurity" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
{{- end -}}

{{- define "table-maintenance.containerSecurity" -}}
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
{{- end -}}

{{- define "table-maintenance.env" -}}
{{- $names := list }}
{{- $entries := dict }}
{{- $own := list }}
{{- with .own }}
{{- $own = fromYamlArray . }}
{{- end }}
{{- range concat $own (.root.Values.global.env | default list) (.role.env | default list) }}
{{- if not (hasKey $entries .name) }}
{{- $names = append $names .name }}
{{- end }}
{{- $_ := set $entries .name . }}
{{- end }}
{{- $out := list }}
{{- range $names }}
{{- $out = append $out (list (get $entries .) | toYaml | trim) }}
{{- end }}
{{- join "\n" $out }}
{{- end -}}

{{- define "table-maintenance.api.env" -}}
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.worker.env" -}}
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.eventConsumer.env" -}}
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.migrate.env" -}}
{{ include "table-maintenance.dbEnv" . }}
{{- end -}}

{{- define "table-maintenance.console.env" -}}
- name: CONSOLE_API_UPSTREAM
  value: http://{{ include "table-maintenance.api.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.backend.api.port }}
{{- end -}}

{{- define "table-maintenance.extraEnvFrom" -}}
{{- with .root.Values.global.envFrom }}
{{ toYaml . }}
{{- end }}
{{- with .role.envFrom }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.secretVolumes" -}}
{{- range $layer, $mounts := dict "global" .root.Values.global.secretMounts "role" .role.secretMounts }}
{{- range $mounts }}
- name: secret-{{ $layer }}-{{ .name }}
  secret:
    secretName: {{ .secretName }}
{{- end }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.secretVolumeMounts" -}}
{{- range $layer, $mounts := dict "global" .root.Values.global.secretMounts "role" .role.secretMounts }}
{{- range $mounts }}
- name: secret-{{ $layer }}-{{ .name }}
  mountPath: {{ .path }}
  readOnly: true
{{- end }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.podScheduling" -}}
{{- with .root.Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .role.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .role.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .role.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.workloadMetadata" -}}
labels:
  {{- include "table-maintenance.labels" . | nindent 2 }}
  {{- with .role.labels }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
{{- with .role.annotations }}
annotations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.podMetadata" -}}
labels:
  {{- include "table-maintenance.labels" . | nindent 2 }}
  {{- with .role.podLabels }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
{{- if or .checksum .role.podAnnotations }}
annotations:
  {{- with .checksum }}
  checksum/config: {{ . }}
  {{- end }}
  {{- with .role.podAnnotations }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.volcano.queue" -}}
{{- default (include "table-maintenance.fullname" .) .Values.maintenance.jobs.scheduling.queues.maintenance.name }}
{{- end -}}

{{- define "table-maintenance.volcano.urgentQueue" -}}
{{- default (include "table-maintenance.suffixed" (dict "root" . "suffix" "urgent")) .Values.maintenance.jobs.scheduling.queues.urgent.name }}
{{- end -}}

{{- define "table-maintenance.volcano.priorityClassPrefix" -}}
{{- default (include "table-maintenance.fullname" .) .Values.maintenance.jobs.scheduling.priorityClassPrefix }}
{{- end -}}

{{- define "table-maintenance.valueAt" -}}
{{- $node := .root.Values }}
{{- range splitList "." .path }}
{{- $node = index ($node | default dict) . }}
{{- end }}
{{- if not (kindIs "invalid" $node) }}{{ $node }}{{ end }}
{{- end -}}

{{- define "table-maintenance.validateValues" -}}
{{- $required := list
  (list "external.database.postgresql.endpoint" "where the PostgreSQL server is, as host:port")
  (list "external.database.postgresql.database" "the database the backend keeps its records in")
  (list "external.database.postgresql.credentialsSecret" "the Secret holding the database username and password")
  (list "external.orchestrator.temporal.endpoint" "where the Temporal frontend is, as host:port")
  (list "external.orchestrator.temporal.namespace" "the Temporal namespace the workflows run in")
  (list "external.catalog.polaris.endpoint" "the Polaris server URL")
  (list "external.catalog.polaris.credentialsSecret" "the Secret holding the Polaris credential")
  (list "external.objectStorage.s3.endpoint" "the S3 endpoint URL")
  (list "external.objectStorage.s3.region" "the S3 region")
  (list "external.objectStorage.s3.credentialsSecret" "the Secret holding the S3 access keys")
  (list "external.catalogEvents.kafka.endpoint" "the Kafka bootstrap servers, as host:port")
  (list "external.catalogEvents.kafka.topic" "the topic Polaris writes its catalog events to")
  (list "external.metricsHistory.prometheus.endpoint" "the Prometheus URL the table metric trends are read from")
  (list "backend.api.httpRoute.gateway.name" "the Gateway the API route attaches to")
  (list "backend.api.httpRoute.gateway.namespace" "the namespace of the Gateway the API route attaches to")
  (list "frontend.console.httpRoute.gateway.name" "the Gateway the console route attaches to")
  (list "frontend.console.httpRoute.gateway.namespace" "the namespace of the Gateway the console route attaches to")
  (list "maintenance.jobs.namespace" "the namespace the Spark operator runs maintenance jobs in")
  (list "maintenance.jobs.spark.eventLogDir" "where Spark writes its event logs, an s3a:// URL") }}
{{- range $required }}
{{- if not (include "table-maintenance.valueAt" (dict "root" $ "path" (index . 0))) }}
{{- fail (printf "%s is required: %s" (index . 0) (index . 1)) }}
{{- end }}
{{- end }}
{{- $named := list
  (list "backend.worker.serviceAccount.create" "backend.worker.serviceAccount.name")
  (list "maintenance.jobs.serviceAccount.create" "maintenance.jobs.serviceAccount.name")
  (list "maintenance.jobs.scheduling.create" "maintenance.jobs.scheduling.queues.maintenance.name")
  (list "maintenance.jobs.scheduling.create" "maintenance.jobs.scheduling.queues.urgent.name")
  (list "maintenance.jobs.scheduling.create" "maintenance.jobs.scheduling.priorityClassPrefix") }}
{{- range $named }}
{{- $create := include "table-maintenance.valueAt" (dict "root" $ "path" (index . 0)) }}
{{- if and (eq $create "false") (not (include "table-maintenance.valueAt" (dict "root" $ "path" (index . 1)))) }}
{{- fail (printf "%s is required when %s is false" (index . 1) (index . 0)) }}
{{- end }}
{{- end }}
{{- $sharedOnly := splitList " " (include "table-maintenance.sharedOnlyKeys" .) }}
{{- range $role := splitList " " (include "table-maintenance.backendRoles" .) }}
{{- range (get $.Values.backend $role).env }}
{{- $given := .name | toString }}
{{- range $sharedOnly }}
{{- if hasPrefix (printf "GLAC_%s__" (upper .)) (upper $given) }}
{{- fail (printf "backend.%s.env %s must be set under maintenance, not per role: the platform settings page shows it" $role $given) }}
{{- end }}
{{- end }}
{{- end }}
{{- end }}
{{- end -}}
