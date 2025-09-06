# Prometheus Deployment

## K8S

There are 3 ways of deploying Prometheus on Kubernetes:

- [prometheus-operator/prometheus-operator](https://github.com/prometheus-operator/prometheus-operator)
- [prometheus-operator/kube-prometheus](https://github.com/prometheus-operator/kube-prometheus)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) in [prometheus-community/helm-charts](https://github.com/prometheus-community/helm-charts)

We use the first option to deploy Prometheus Operator using YAML files.


## References

- [Thanos and the Prometheus Operator | Prometheus Operator Docs](https://prometheus-operator.dev/docs/platform/thanos/)
- [Design | Thanos Docs](https://thanos.io/tip/thanos/design.md/)