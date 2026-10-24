# polaris-routes

Installs the north-south routing layer for Polaris via a single Envoy-backed `Gateway` and one catch-all `HTTPRoute`. External clients hit the ingress on port 80 and every request reaches Polaris. The table-maintenance control plane API is not exposed through this Gateway; it runs in `lakehouse-control-plane` (see `platform/25-lakehouse-control-plane`).

Service-to-service (east-west) traffic — for example the backend calling Polaris — does NOT go through this Gateway. In-cluster consumers use Service DNS directly (e.g. `polaris.lakehouse-catalog.svc.cluster.local:8181`).

## Deployed Resources

```
Namespace: istio-ingress
└── platform-gateway  (Gateway)

Namespace: lakehouse-catalog
└── polaris-catchall  (HTTPRoute, catch-all → polaris:8181)
```

## Namespaces

- `istio-ingress` (Gateway, existing — created by `12-istio-ingressgw`)
- `lakehouse-catalog` (HTTPRoute, existing — created by `21-polaris`)

## Access

Istio's Gateway API implementation auto-creates a `Deployment` + `Service` named `platform-gateway-istio` for this Gateway (not to be confused with the legacy `istio-ingressgateway` installed by `12-istio-ingressgw`, which serves the legacy `networking.istio.io/v1beta1` Gateway CRD). The `networking.istio.io/service-type: ClusterIP` annotation on this Gateway forces the auto-created Service to `ClusterIP` (otherwise it defaults to `LoadBalancer` which stays `<pending>` on minikube).

To reach it from a laptop:
`kubectl port-forward svc/platform-gateway-istio -n istio-ingress 8080:80 --context <ctx>`
