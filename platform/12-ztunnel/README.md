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
