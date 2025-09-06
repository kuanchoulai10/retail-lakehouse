
# OpenTelemetry Deployment

There are 2 ways of deploying OpenTelemetry Collector on Kubernetes:

- [OpenTelemetry Collector Chart](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/). This helm chart can be used to install a collector as a `Deployment`, `Daemonset`, or `Statefulset`.
- [OpenTelemetry Operator for Kubernetes](https://opentelemetry.io/docs/platforms/kubernetes/operator/)


!!! note

    By default, `opentelemetry-operator` uses the [`opentelemetry-collector` image](https://github.com/open-telemetry/opentelemetry-collector-releases/pkgs/container/opentelemetry-collector-releases%2Fopentelemetry-collector). When the operator is installed using Helm charts, the [`opentelemetry-collector-k8s` image](https://github.com/open-telemetry/opentelemetry-collector-releases/pkgs/container/opentelemetry-collector-releases%2Fopentelemetry-collector-k8s) is used. If you need a component not found in these releases, you may need to build your own collector.