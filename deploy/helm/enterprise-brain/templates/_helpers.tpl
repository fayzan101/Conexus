{{- define "eb.name" -}}
enterprise-brain
{{- end -}}

{{- define "eb.labels" -}}
app.kubernetes.io/name: {{ include "eb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}
