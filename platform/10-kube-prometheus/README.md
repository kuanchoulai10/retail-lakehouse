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

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `grafana` | 3000 | Grafana web UI |
| `prometheus-k8s` | 9090, 8080 | Prometheus query API and web UI |
| `alertmanager-main` | 9093, 8080 | Alertmanager API and web UI |
| `prometheus-adapter` | 443 | Custom metrics API server |
| `blackbox-exporter` | 9115, 19115 | Blackbox probe HTTP endpoint |
| `kube-state-metrics` | 8443, 9443 | Kubernetes object metrics (headless) |
| `node-exporter` | 9100 | Per-node metrics (headless) |
| `prometheus-operated` | 9090 | Headless service for Prometheus StatefulSet |
| `alertmanager-operated` | 9093, 9094 | Headless service for Alertmanager StatefulSet |
| `prometheus-operator` | 8443 | Prometheus Operator metrics (headless) |

## CRDs

| CRD | Purpose |
|-----|---------|
| `prometheuses.monitoring.coreos.com` | Declares a Prometheus instance |
| `prometheusagents.monitoring.coreos.com` | Declares an agent-mode Prometheus instance |
| `alertmanagers.monitoring.coreos.com` | Declares an Alertmanager instance |
| `alertmanagerconfigs.monitoring.coreos.com` | Configures Alertmanager routing and receivers |
| `servicemonitors.monitoring.coreos.com` | Configures Prometheus scrape targets from Services |
| `podmonitors.monitoring.coreos.com` | Configures Prometheus scrape targets from Pods |
| `prometheusrules.monitoring.coreos.com` | Declares alerting and recording rules |
| `probes.monitoring.coreos.com` | Configures blackbox probe targets |
| `scrapeconfigs.monitoring.coreos.com` | Declares raw Prometheus scrape configurations |
| `thanosrulers.monitoring.coreos.com` | Declares a Thanos Ruler instance |
