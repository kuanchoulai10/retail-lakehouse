# ztunnel

Installs the Istio ambient L4 proxy (ztunnel) via the `istio/ztunnel` Helm chart. Runs as a DaemonSet on every node and terminates/originates mTLS for ambient-enrolled workloads. `profile: ambient` is not a valid values key for ztunnel (ztunnel is ambient-only), but `global.platform=minikube` is still required for minikube's docker driver.

## Deployed Resources

```
Namespace: istio-system
└── ztunnel  (DaemonSet, one pod per node)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `ztunnel` | Ambient-mode L4 proxy; establishes HBONE mTLS tunnels between nodes |

## Metrics

`ztunnel-podmonitor.yaml` is a PodMonitor that makes kube-prometheus scrape each ztunnel pod on port
`ztunnel-stats` (:15020) at `/metrics`, which is where the `istio_tcp_*` series come from (Kiali's graph reads
them). `ztunnel-prometheus-rbac.yaml` is a Role / RoleBinding that lets `prometheus-k8s` list pods in
`istio-system`; without it Prometheus cannot discover the ztunnel targets.

## Enrolment

A namespace joins the ambient mesh (L4 only) through the label `istio.io/dataplane-mode=ambient`. Enrolled:
`kafka-ui`, `ecommerce-app`, `object-storage`, `lakehouse-catalog`, `kafka`, `lakehouse-query-engine`,
`temporal`, `lakehouse-control-plane`, `lakehouse-maintenance-operations`. Each wave that creates one of them
uses `namespace::apply_ambient` from `scripts/utils/namespace.sh` and asserts the label in its `validate.sh` with
`namespace::assert_ambient`. Never labelled: `kube-system`, `istio-system`, `istio-ingress`, `monitoring` and the
operator namespaces.

On containerd, istio-cni must be installed with `cni.cniNetnsDir: /var/run/netns` (`12-istio-cni`); otherwise
enrolled pods hang in ContainerCreating.

## HBONE check

`mesh::assert_hbone <namespace>` port-forwards to the node's ztunnel admin port (:15000), reads `/config_dump`
and fails unless every Running pod of the namespace is listed with `protocol: HBONE`:

```bash
KUBE_CONTEXT=retail-lakehouse bash -c '
  source scripts/utils/namespace.sh
  for ns in kafka-ui ecommerce-app object-storage lakehouse-catalog kafka lakehouse-query-engine \
    temporal lakehouse-control-plane lakehouse-maintenance-operations; do
    mesh::assert_hbone "$ns"
  done'
```

`lakehouse-maintenance-operations` holds only short-lived Spark driver and executor pods, so at rest it has
no Running pods and the check fails there with `no Running pods in namespace`. That is expected; run the check
for that namespace while a maintenance job is running.
