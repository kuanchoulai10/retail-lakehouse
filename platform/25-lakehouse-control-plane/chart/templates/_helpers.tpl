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
      name: {{ .Values.postgres.secretName }}
      key: {{ .Values.postgres.secretKey }}
- name: GLAC_POSTGRES__DB_URL
  value: postgresql+psycopg://{{ .Values.postgres.user }}:$(DB_PASSWORD)@table-maintenance-db:5432/{{ .Values.postgres.database }}
{{- end -}}

{{- define "table-maintenance.appEnv" -}}
{{ include "table-maintenance.dbEnv" . }}
- name: GLAC_CATALOG__CREDENTIAL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secrets.catalogCredential }}
      key: credential
{{- end -}}

{{- define "table-maintenance.waitForSchema" -}}
- name: wait-for-schema
  image: {{ .Values.postgres.image }}
  imagePullPolicy: IfNotPresent
  env:
    - name: PGPASSWORD
      valueFrom:
        secretKeyRef:
          name: {{ .Values.postgres.secretName }}
          key: {{ .Values.postgres.secretKey }}
  command:
    - sh
    - -c
    - >-
      until [ "$(psql -h table-maintenance-db -U {{ .Values.postgres.user }} -d {{ .Values.postgres.database }} -tAc "select (select count(*) from table_maintenance_policies where name = 'default') + (select count(*) from table_discovery_policies where id = 'dp-00000000000000000000000000')")" = "2" ]; do
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
