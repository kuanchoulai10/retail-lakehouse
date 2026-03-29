# KEDA

Deploys KEDA (Kubernetes Event-Driven Autoscaling) via Helm. KEDA extends Kubernetes with event-driven autoscaling by bridging external event sources (Kafka, Prometheus, cron, etc.) to the Horizontal Pod Autoscaler. TLS certificates for its admission webhooks are managed by cert-manager.

## Deployed Resources

```
Namespace: keda
├── keda-operator                        (Deployment)
├── keda-operator-metrics-apiserver      (Deployment)
└── keda-admission-webhooks              (Deployment)
```

## Namespaces

- `keda`

## Pods

| Pod | Purpose |
|-----|---------|
| `keda-operator` | Watches ScaledObjects and drives HPA scaling |
| `keda-operator-metrics-apiserver` | Serves external metrics to the Kubernetes metrics API |
| `keda-admission-webhooks` | Validates ScaledObject and TriggerAuthentication resources |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `keda-operator` | 9666 | Operator metrics endpoint |
| `keda-operator-metrics-apiserver` | 443, 8080 | External metrics API and health endpoint |
| `keda-admission-webhooks` | 443 | Admission webhook for ScaledObject validation |

## CRDs

| CRD | Purpose |
|-----|---------|
| `scaledobjects.keda.sh` | Maps an event source to a Deployment or StatefulSet scaler |
| `scaledjobs.keda.sh` | Scales Kubernetes Jobs based on event source queue depth |
| `triggerauthentications.keda.sh` | Stores authentication credentials for event source triggers |
| `clustertriggerauthentications.keda.sh` | Cluster-scoped variant of TriggerAuthentication |
| `cloudeventsources.eventing.keda.sh` | Configures CloudEvent-based scaling triggers |
| `clustercloudeventsources.eventing.keda.sh` | Cluster-scoped variant of CloudEventSource |
