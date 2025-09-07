# Thanos Deployment

## K8S

There are 3 ways of deploying Thanos on Kubernetes:

- [Community Helm charts](https://artifacthub.io/packages/search?ts_query_web=thanos)
- [prometheus-operator](https://github.com/coreos/prometheus-operator)
- [kube-thanos](https://github.com/thanos-io/kube-thanos): Jsonnet based Kubernetes templates.

We use **Bitnami Thanos Helm chart** to deploy Thanos components.

## References

- [Community Thanos Kubernetes Applications | Thanos Docs](https://thanos.io/tip/thanos/getting-started.md/#community-thanos-kubernetes-applications) 