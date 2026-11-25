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

{{- define "table-maintenance.roleConfig.enabled" -}}
{{- $values := .root.Values }}
{{- if eq .role "migrate" }}
{{- if or $values.migrate.enabled $values.api.enabled $values.worker.enabled $values.eventConsumer.enabled }}true{{ end }}
{{- else if (get $values .role).enabled }}true
{{- end }}
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

{{- define "table-maintenance.chartConfig" -}}
{{- $values := .Values }}
{{- $spark := dict
  "image" (include "table-maintenance.image" (dict "root" . "image" $values.image.spark))
  "image_pull_policy" $values.image.pullPolicy
  "service_account" (include "table-maintenance.spark.serviceAccountName" .)
  "catalog_credential_secret" $values.secrets.catalogCredential
  "s3_secret_name" $values.secrets.s3
  "namespace" $values.namespaces.maintenanceOperations
  "volcano" (dict
    "queue" (include "table-maintenance.volcano.queue" .)
    "urgent_queue" (include "table-maintenance.volcano.urgentQueue" .)
    "priority_class_prefix" (include "table-maintenance.volcano.priorityClassPrefix" .)) }}
{{- range $size, $key := dict "S" "size_s" "M" "size_m" "L" "size_l" }}
{{- $given := index ($values.spark.sizes | default dict) $size | default dict }}
{{- $out := dict }}
{{- range $from, $to := dict "driverMemory" "driver_memory" "executorMemory" "executor_memory" "executorInstances" "executor_instances" }}
{{- $value := index $given $from }}
{{- if not (kindIs "invalid" $value) }}
{{- $_ := set $out $to $value }}
{{- end }}
{{- end }}
{{- if $out }}
{{- $_ := set $spark $key $out }}
{{- end }}
{{- end }}
{{- $config := dict
  "database" (dict "backend" "postgres")
  "spark" $spark
  "callback_base_url" (printf "http://%s.%s.svc.cluster.local:%v" (include "table-maintenance.api.fullname" .) .Release.Namespace $values.api.port)
  "http" (dict "root_path" $values.api.rootPath) }}
{{- $maintenance := dict }}
{{- range $from, $to := dict "attemptDeadlineSeconds" "attempt_deadline_seconds" "maxAttempts" "max_attempts" "queueWaitLimitSeconds" "queue_wait_limit_seconds" }}
{{- $value := index ($values.maintenance | default dict) $from }}
{{- if not (kindIs "invalid" $value) }}
{{- $_ := set $maintenance $to $value }}
{{- end }}
{{- end }}
{{- if $maintenance }}
{{- $_ := set $config "maintenance" $maintenance }}
{{- end }}
{{- with $values.logLevel }}
{{- $_ := set $config "log_level" . }}
{{- end }}
{{- toYaml $config }}
{{- end -}}

{{- define "table-maintenance.roleConfig" -}}
{{- $root := .root }}
{{- $merged := mergeOverwrite (dict)
  (include "table-maintenance.chartConfig" $root | fromYaml)
  (deepCopy ($root.Values.config | default dict))
  (deepCopy ((get $root.Values .role).config | default dict)) }}
{{- $out := dict }}
{{- range splitList " " (include "table-maintenance.roleKeys" .role) }}
{{- if hasKey $merged . }}
{{- $_ := set $out . (get $merged .) }}
{{- end }}
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
{{- default (include "table-maintenance.worker.fullname" .) .Values.worker.serviceAccount.name }}
{{- end -}}

{{- define "table-maintenance.spark.serviceAccountName" -}}
{{- default (include "table-maintenance.suffixed" (dict "root" . "suffix" "spark")) .Values.spark.serviceAccount.name }}
{{- end -}}

{{- define "table-maintenance.imageTag" -}}
{{- default .root.Chart.AppVersion .image.tag }}
{{- end -}}

{{- define "table-maintenance.image" -}}
{{- with .root.Values.image.registry }}{{ . }}/{{ end }}
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

{{- define "table-maintenance.dbEnv" -}}
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Values.database.existingSecret }}
      key: {{ .Values.database.secretKey }}
- name: GLAC_DATABASE__POSTGRES__DB_URL
  value: postgresql+psycopg://{{ .Values.database.user }}:$(DB_PASSWORD)@{{ .Values.database.host }}:{{ .Values.database.port }}/{{ .Values.database.name }}
{{- end -}}

{{- define "table-maintenance.appEnv" -}}
{{ include "table-maintenance.dbEnv" . }}
- name: GLAC_CATALOG__CREDENTIAL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secrets.catalogCredential }}
      key: credential
{{- end -}}

{{- define "table-maintenance.waitForDatabase" -}}
- name: wait-for-db
  image: {{ .Values.database.clientImage }}
  imagePullPolicy: IfNotPresent
  command:
    - sh
    - -c
    - until pg_isready -h {{ .Values.database.host }} -p {{ .Values.database.port }} -U {{ .Values.database.user }} -d {{ .Values.database.name }}; do sleep 2; done
{{- end -}}

{{- define "table-maintenance.waitForSchema" -}}
- name: wait-for-schema
  image: {{ include "table-maintenance.image" (dict "root" . "image" .Values.image.backend) }}
  imagePullPolicy: {{ .Values.image.pullPolicy }}
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
{{- range concat $own (.root.Values.env | default list) (.role.env | default list) }}
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
  value: http://{{ include "table-maintenance.api.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.api.port }}
{{- end -}}

{{- define "table-maintenance.extraEnvFrom" -}}
{{- with .root.Values.envFrom }}
{{ toYaml . }}
{{- end }}
{{- with .role.envFrom }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.secretVolumes" -}}
{{- range $layer, $mounts := dict "global" .root.Values.secretMounts "role" .role.secretMounts }}
{{- range $mounts }}
- name: secret-{{ $layer }}-{{ .name }}
  secret:
    secretName: {{ .secretName }}
{{- end }}
{{- end }}
{{- end -}}

{{- define "table-maintenance.secretVolumeMounts" -}}
{{- range $layer, $mounts := dict "global" .root.Values.secretMounts "role" .role.secretMounts }}
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
{{- default (include "table-maintenance.fullname" .) .Values.volcano.queues.maintenance.name }}
{{- end -}}

{{- define "table-maintenance.volcano.urgentQueue" -}}
{{- default (include "table-maintenance.suffixed" (dict "root" . "suffix" "urgent")) .Values.volcano.queues.urgent.name }}
{{- end -}}

{{- define "table-maintenance.volcano.priorityClassPrefix" -}}
{{- default (include "table-maintenance.fullname" .) .Values.volcano.priorityClassPrefix }}
{{- end -}}

{{- define "table-maintenance.validateValues" -}}
{{- if not .Values.database.existingSecret }}
{{- fail "database.existingSecret is required: the chart creates no password Secret; bootstrap.sh of platform/20-table-maintenance-db does" }}
{{- end }}
{{- if and .Values.console.enabled (not .Values.api.enabled) }}
{{- fail "console.enabled needs api.enabled: the console sends /console/api to the API" }}
{{- end }}
{{- if and .Values.worker.enabled (not .Values.api.enabled) }}
{{- fail "worker.enabled needs api.enabled: Spark jobs send their results to the API" }}
{{- end }}
{{- if gt (int .Values.eventConsumer.replicas) 1 }}
{{- fail "eventConsumer.replicas must be 0 or 1: Polaris events are consumed by one consumer" }}
{{- end }}
{{- if and .Values.worker.enabled (not .Values.worker.serviceAccount.create) (not .Values.worker.serviceAccount.name) }}
{{- fail "worker.serviceAccount.name is required when worker.serviceAccount.create is false" }}
{{- end }}
{{- if and .Values.worker.enabled (not .Values.spark.serviceAccount.create) (not .Values.spark.serviceAccount.name) }}
{{- fail "spark.serviceAccount.name is required when spark.serviceAccount.create is false" }}
{{- end }}
{{- $roles := splitList " " (include "table-maintenance.backendRoles" .) }}
{{- $sharedOnly := splitList " " (include "table-maintenance.sharedOnlyKeys" .) }}
{{- $anyRole := list }}
{{- range $roles }}
{{- $anyRole = concat $anyRole (splitList " " (include "table-maintenance.roleKeys" .)) }}
{{- end }}
{{- range $key, $_ := .Values.config }}
{{- if not (has $key $anyRole) }}
{{- fail (printf "config.%s is not a setting of any role" $key) }}
{{- end }}
{{- end }}
{{- $secrets := list (list "database" "postgres" "db_url") (list "catalog" "credential") (list "catalog" "s3_access_key_id") (list "catalog" "s3_secret_access_key") }}
{{- $sources := list (list "config" .Values.config) }}
{{- range $roles }}
{{- $sources = append $sources (list (printf "%s.config" .) (get $.Values .).config) }}
{{- end }}
{{- range $source := $sources }}
{{- range $path := $secrets }}
{{- $node := index $source 1 | default dict }}
{{- $found := true }}
{{- range $path }}
{{- if and $found (kindIs "map" $node) (hasKey $node .) }}
{{- $node = index $node . }}
{{- else }}
{{- $found = false }}
{{- end }}
{{- end }}
{{- if and $found (not (kindIs "invalid" $node)) }}
{{- fail (printf "%s.%s is a secret: it comes from the environment, not the settings file" (index $source 0) (join "." $path)) }}
{{- end }}
{{- end }}
{{- end }}
{{- range $role := $roles }}
{{- range (get $.Values $role).env }}
{{- $given := .name | toString }}
{{- range $sharedOnly }}
{{- if hasPrefix (printf "GLAC_%s__" (upper .)) (upper $given) }}
{{- fail (printf "%s.env %s must be set in config, not per role: the platform settings page shows it" $role $given) }}
{{- end }}
{{- end }}
{{- end }}
{{- end }}
{{- range $role := $roles }}
{{- $keys := splitList " " (include "table-maintenance.roleKeys" $role) }}
{{- range $key, $_ := (get $.Values $role).config }}
{{- if has $key $sharedOnly }}
{{- fail (printf "%s.config.%s must be set in config, not per role: the platform settings page shows it" $role $key) }}
{{- else if not (has $key $keys) }}
{{- fail (printf "%s.config.%s is not a setting of %s" $role $key $role) }}
{{- end }}
{{- end }}
{{- end }}
{{- end -}}
