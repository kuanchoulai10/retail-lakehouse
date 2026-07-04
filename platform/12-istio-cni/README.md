# istio-cni

Installs the Istio CNI node agent in ambient profile via the `istio/cni` Helm chart. Runs as a DaemonSet on every node and programs the host's iptables/nftables to redirect ambient-mode workload traffic into ztunnel. Requires `global.platform=minikube` to place the CNI binary/config in minikube-compatible directories.

## Deployed Resources

```
Namespace: istio-system
└── istio-cni-node  (DaemonSet, one pod per node)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `istio-cni-node` | CNI plugin installer + node-agent that programs ambient traffic redirection |
