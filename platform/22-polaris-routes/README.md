# polaris-routes

Installs the north-south routing layer for Polaris + table-maintenance-backend via a single Envoy-backed `Gateway` and two `HTTPRoute`s. External clients hit the ingress on port 80; requests matching `/v1/*` reach the table-maintenance backend, and everything else falls through to Polaris.

Service-to-service (east-west) traffic — for example the backend calling Polaris — does NOT go through this Gateway. In-cluster consumers use Service DNS directly (e.g. `polaris.polaris.svc.cluster.local:8181`).

## Deployed Resources

```
Namespace: istio-ingress
└── platform-gateway  (Gateway)

Namespace: polaris
├── polaris-catchall  (HTTPRoute, catch-all → polaris:8181)
└── backend-route     (HTTPRoute, /v1/ → table-maintenance-backend:8000)
```

## Namespaces

- `istio-ingress` (Gateway, existing — created by `12-istio-ingressgw`)
- `polaris` (HTTPRoutes, existing — created by `21-polaris`)

## Access

Istio's Gateway API implementation auto-creates a `Deployment` + `Service` named `platform-gateway-istio` for this Gateway (not to be confused with the legacy `istio-ingressgateway` installed by `12-istio-ingressgw`, which serves the legacy `networking.istio.io/v1beta1` Gateway CRD). The `networking.istio.io/service-type: ClusterIP` annotation on this Gateway forces the auto-created Service to `ClusterIP` (otherwise it defaults to `LoadBalancer` which stays `<pending>` on minikube).

To reach it from a laptop:
`kubectl port-forward svc/platform-gateway-istio -n istio-ingress 8080:80 --context <ctx>`
