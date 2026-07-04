# istio-ingressgw

Installs an Istio ingress gateway (Envoy) via the `istio/gateway` Helm chart into a dedicated `istio-ingress` namespace, isolated from the control plane. Service is `ClusterIP` in this iteration — no external exposure. Future work: attach a `Gateway` + `HTTPRoute` (from `platform/26-platform-routes/`) that terminates HTTP traffic and routes to Polaris (default) and the table-maintenance backend (specific prefixes).

## Deployed Resources

```
Namespace: istio-ingress
├── istio-ingressgateway  (Deployment)
└── istio-ingressgateway  (Service, ClusterIP)
```

## Namespaces

- `istio-ingress` (created; separate from `istio-system` on purpose)

## Pods

| Pod | Purpose |
|-----|---------|
| `istio-ingressgateway` | Envoy proxy that terminates inbound traffic bound to a `Gateway` resource |

## Services

| Service | Type | Port | Purpose |
|---------|------|------|---------|
| `istio-ingressgateway` | ClusterIP | 15021 | Health check |
| `istio-ingressgateway` | ClusterIP | 80 | HTTP inbound |
| `istio-ingressgateway` | ClusterIP | 443 | HTTPS inbound |
