# istio-base

Installs Istio's base CRDs and cluster roles into the `istio-system` namespace via the `istio/base` Helm chart. This is the foundation layer — it must be installed before `istiod`, `istio-cni`, or `ztunnel`.

## Deployed Resources

```
Namespace: istio-system
└── (CRDs and ClusterRoles only; no workloads)
```

## Namespaces

- `istio-system` (created)

## CRDs

| CRD | Purpose |
|-----|---------|
| `virtualservices.networking.istio.io` | Layer-7 routing rules |
| `gateways.networking.istio.io` | Ingress/egress traffic entry points |
| `destinationrules.networking.istio.io` | Load balancing, connection pool, TLS settings |
| `peerauthentications.security.istio.io` | Mesh-side mTLS policy |
| `authorizationpolicies.security.istio.io` | Access control between workloads |
| (~20 additional Istio CRDs) | Telemetry, ServiceEntry, Sidecar, WasmPlugin, ProxyConfig, ... |
