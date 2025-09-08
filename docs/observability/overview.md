# Overview

![](./assets/metrics.excalidraw.svg){width=600}
/// caption
Architecture Overview
///

!!! success "Metrics Collection Deployment Steps"

    - [ ] Deploy a Prometheus Operator using YAML files
    - [ ] Deploy a Thanos using bitnami helm chart (Receiver, Store Gateway, Querier, Compactor, )
    - [ ] Deploy a Thanos ruler using Prometheus Operator
    - [ ] Deploy a Prometheus Alertmanager using Prometheus Operator
    - [ ] Deploy a OpenTelemetry Operator
    - [ ] Deploy a OpenTelemetry Collector using OpenTelemetry Operator
    - [ ] Deploy a Grafana using helm chart

```bash
cd ~/Projects/retail-lakehouse/observability
bash ./install.sh
```

The `install.sh` script in the `observability` directory is as follows:

??? info "install.sh"

    ```bash
    --8<-- "./retail-lakehouse/observability/install.sh"
    ```

---

## Manually

```bash
kubectl apply -f manifests/prometheus-alertmanager.yaml
kubectl get all -n thanos
```

!!! info "Result"

    ```
    NAME                                  READY   STATUS    RESTARTS   AGE
    pod/alertmanager-alertmanager-sre-0   2/2     Running   0          2m2s
    pod/alertmanager-alertmanager-sre-1   2/2     Running   0          2m2s

    NAME                            TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                      AGE
    service/alertmanager-operated   ClusterIP   None         <none>        9093/TCP,9094/TCP,9094/UDP   2m2s

    NAME                                             READY   AGE
    statefulset.apps/alertmanager-alertmanager-sre   2/2     2m2s
    ```


```bash
kubectl apply -f manifests/memcached.yaml
k get all -n thanos
```

!!! info "Result"

    ```
    NAME                                  READY   STATUS    RESTARTS   AGE
    pod/alertmanager-alertmanager-sre-0   2/2     Running   0          6m22s
    pod/alertmanager-alertmanager-sre-1   2/2     Running   0          6m22s
    pod/memcached-0                       1/1     Running   0          44s
    pod/memcached-1                       1/1     Running   0          33s
    pod/memcached-2                       1/1     Running   0          22s

    NAME                            TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                      AGE
    service/alertmanager-operated   ClusterIP   None         <none>        9093/TCP,9094/TCP,9094/UDP   6m22s
    service/memcached               ClusterIP   None         <none>        11211/TCP                    44s

    NAME                                             READY   AGE
    statefulset.apps/alertmanager-alertmanager-sre   2/2     6m22s
    statefulset.apps/memcached                       3/3     44s
    ```


!!! success "Traces Collection Deployment Steps"

    - [ ] Deploy a Jaeger
    - [ ] Deploy a OpenTelemetry Collector
    - [ ] Trino jmx


