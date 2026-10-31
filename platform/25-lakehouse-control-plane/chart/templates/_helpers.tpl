{{- define "table-maintenance.backendImage" -}}
{{ .Values.image.backend.repository }}:{{ required "image.backend.tag is required" .Values.image.backend.tag }}
{{- end -}}

{{- define "table-maintenance.sparkImage" -}}
{{ .Values.image.spark.repository }}:{{ required "image.spark.tag is required" .Values.image.spark.tag }}
{{- end -}}

{{- define "table-maintenance.consoleImage" -}}
{{ .Values.image.console.repository }}:{{ required "image.console.tag is required" .Values.image.console.tag }}
{{- end -}}

{{- define "table-maintenance.labels" -}}
app.kubernetes.io/name: table-maintenance
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
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
      until [ "$(psql -h table-maintenance-db -U {{ .Values.postgres.user }} -d {{ .Values.postgres.database }} -tAc "select count(*) from table_maintenance_presets where name = 'default'")" = "1" ]; do
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
