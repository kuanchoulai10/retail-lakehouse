---
tags:
  - Prometheus
  - SRE
---

# How Prometheus Works?

## Architecture Components

![](https://prometheus.io/assets/docs/architecture.svg)
/// caption
[Architecture Overview](https://prometheus.io/docs/introduction/overview/#architecture)
///

- the main **Prometheus server** which scrapes and stores time series data
- **client libraries** for instrumenting application code
- a **push gateway** for supporting short-lived jobs
- special-purpose **exporters** for services like HAProxy, StatsD, Graphite, etc.
- an **alertmanager** to handle alerts
- various support tools

## Prometheus Agent

> *Prometheus Agent is a deployment model optimized for environments where all collected data is forwarded to a long-term storage solution.*

Similarly to Prometheus, Prometheus Agent will also require permission to scrape targets. Because of this, we will create a new service account for the Agent with the necessary permissions to scrape targets.

See [Introducing Prometheus Agent Mode, an Efficient and Cloud-Native Way for Metric Forwarding](https://prometheus.io/blog/2021/11/16/agent/) for more details.

## Kubernetes

There are 3 ways of deploying Prometheus on Kubernetes:

- [prometheus-operator/prometheus-operator](https://github.com/prometheus-operator/prometheus-operator)
- [prometheus-operator/kube-prometheus](https://github.com/prometheus-operator/kube-prometheus)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) in [prometheus-community/helm-charts](https://github.com/prometheus-community/helm-charts)

We use the Prometheus Operator to deploy partial components of Prometheus in this project.


## Core Concepts


## Behind the Scenes




## References


