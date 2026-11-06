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

## Extension providers

Mesh config registers the ext_authz provider `oauth2-proxy` (`envoyExtAuthzHttp`, `oauth2-proxy.identity.svc.cluster.local:4180`). It forwards the original request path, so oauth2-proxy can build its redirect, and returns `location`, `set-cookie` and `content-type` on deny. Each check times out after 5 s (`timeout: 5s`; Istio's default is 600 s), and a timeout denies. Nothing references it until an `AuthorizationPolicy` with action `CUSTOM` names it.
