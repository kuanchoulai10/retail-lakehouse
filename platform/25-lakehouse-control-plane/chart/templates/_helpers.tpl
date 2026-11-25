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

{{- define "table-maintenance.config.fullname" -}}
{{- include "table-maintenance.suffixed" (dict "root" . "suffix" "config") }}
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
- name: GLAC_POSTGRES__DB_URL
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
  image: {{ .Values.database.clientImage }}
  imagePullPolicy: IfNotPresent
  env:
    - name: PGPASSWORD
      valueFrom:
        secretKeyRef:
          name: {{ .Values.database.existingSecret }}
          key: {{ .Values.database.secretKey }}
  command:
    - sh
    - -c
    - >-
      until [ "$(psql -h {{ .Values.database.host }} -p {{ .Values.database.port }} -U {{ .Values.database.user }} -d {{ .Values.database.name }} -tAc "select (select count(*) from table_maintenance_policies where name = 'default') + (select count(*) from table_discovery_policies where id = 'dp-00000000000000000000000000')")" = "2" ]; do
      echo "waiting for the migrate job to seed the schema"; sleep 3; done
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
- name: GLAC_COMPONENT
  value: api
- name: GLAC_API__ROOT_PATH
  value: {{ .Values.api.rootPath | quote }}
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.worker.env" -}}
- name: GLAC_COMPONENT
  value: worker
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.eventConsumer.env" -}}
- name: GLAC_COMPONENT
  value: event_consumer
{{ include "table-maintenance.appEnv" . }}
{{- end -}}

{{- define "table-maintenance.migrate.env" -}}
- name: GLAC_COMPONENT
  value: migrate
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
{{- end -}}
