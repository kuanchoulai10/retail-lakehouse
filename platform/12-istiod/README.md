# istiod

Installs the Istio control plane (istiod) in ambient profile via the `istio/istiod` Helm chart. istiod issues workload certificates and pushes xDS configuration to ztunnel (and future waypoint proxies). Configured with `global.platform=minikube` to work around minikube's non-standard docker-driver bind-mount paths.

## Deployed Resources

```
Namespace: istio-system
└── istiod  (Deployment)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `istiod` | Control plane: config generation, CA, xDS server, sidecar injector webhook |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `istiod` | 15010 | Plaintext xDS (legacy) |
| `istiod` | 15012 | mTLS xDS (used by ztunnel and waypoints) |
| `istiod` | 15014 | Monitoring |
| `istiod` | 15017 | Sidecar-injector webhook |
