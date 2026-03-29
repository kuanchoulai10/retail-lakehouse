# kube-prometheus

Deploys the full kube-prometheus monitoring stack using the official [kube-prometheus](https://github.com/prometheus-operator/kube-prometheus) project. This includes the Prometheus Operator, a Prometheus instance, Alertmanager, Grafana, and supporting exporters for cluster-wide observability.

## Deployed Resources

```
Namespace: monitoring
├── prometheus-operator                  (Deployment)
├── prometheus-k8s                       (StatefulSet)
├── alertmanager-main                    (StatefulSet)
├── grafana                              (Deployment)
├── kube-state-metrics                   (Deployment)
├── prometheus-adapter                   (Deployment)
├── blackbox-exporter                    (Deployment)
└── node-exporter                        (DaemonSet)
```

## Namespaces

- `monitoring`

## Pods

| Pod | Purpose |
|-----|---------|
| `prometheus-operator` | Manages Prometheus and Alertmanager resources |
| `prometheus-k8s` | Scrapes and stores metrics |
| `alertmanager-main` | Routes and deduplicates alerts |
| `grafana` | Visualizes metrics |
| `kube-state-metrics` | Exposes Kubernetes object metrics |
| `prometheus-adapter` | Serves custom metrics API for HPA |
| `blackbox-exporter` | Probes endpoints over HTTP, TCP, and ICMP |
| `node-exporter` | Exposes per-node hardware and OS metrics |

## CRDs

| CRD | Purpose |
|-----|---------|
| `prometheuses.monitoring.coreos.com` | Declares a Prometheus instance |
| `alertmanagers.monitoring.coreos.com` | Declares an Alertmanager instance |
| `servicemonitors.monitoring.coreos.com` | Configures Prometheus scrape targets from Services |
| `podmonitors.monitoring.coreos.com` | Configures Prometheus scrape targets from Pods |
| `prometheusrules.monitoring.coreos.com` | Declares alerting and recording rules |
| `probes.monitoring.coreos.com` | Configures blackbox probe targets |
| `thanosrulers.monitoring.coreos.com` | Declares a Thanos Ruler instance |
