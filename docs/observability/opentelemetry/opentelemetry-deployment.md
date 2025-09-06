
# OpenTelemetry Deployment

## Deployment Patterns

Patterns you can apply to deploy the OpenTelemetry collector:

- No Collector
- Agent
- Gateway

![](https://opentelemetry.io/docs/collector/img/otel-sdk.svg){width=600}
/// caption
[No Collector](https://opentelemetry.io/docs/collector/deployment/no-collector/)
///

![](https://opentelemetry.io/docs/collector/img/otel-agent-sdk.svg){width=600}
/// caption
[Agent](https://opentelemetry.io/docs/collector/deployment/agent/)
///

![](https://opentelemetry.io/docs/collector/img/otel-gateway-sdk.svg){width=600}
/// caption
[Gateway](https://opentelemetry.io/docs/collector/deployment/gateway/)
///

## K8S

There are 2 ways of deploying OpenTelemetry Collector on Kubernetes:

- [OpenTelemetry Collector Helm Chart](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/). This helm chart can be used to install a collector as a `Deployment`, `Daemonset`, or `Statefulset`.
- [OpenTelemetry Operator for Kubernetes](https://opentelemetry.io/docs/platforms/kubernetes/operator/)


!!! note

    By default, `opentelemetry-operator` uses the [`opentelemetry-collector` image](https://github.com/open-telemetry/opentelemetry-collector-releases/pkgs/container/opentelemetry-collector-releases%2Fopentelemetry-collector). When the operator is installed using Helm charts, the [`opentelemetry-collector-k8s` image](https://github.com/open-telemetry/opentelemetry-collector-releases/pkgs/container/opentelemetry-collector-releases%2Fopentelemetry-collector-k8s) is used. If you need a component not found in these releases, you may need to build your own collector.

You can refer to the [Install the Collector | OpenTelemetry Docs](https://opentelemetry.io/docs/collector/installation/#kubernetes) and [Kubernetes Getting Started | OpenTelemetry Docs](https://opentelemetry.io/docs/platforms/kubernetes/getting-started/) for more details.


We'll use `OpenTelemetry Operator for Kubernetes` to deploy OpenTelemetry Collector.