# platform-gateway

The single north-south entry point of the platform: one Gateway API `Gateway` in `istio-ingress`, backed by an Envoy that Istio creates for it. The listener accepts any hostname and routes by path: each web UI or API gets its own path prefix, so one origin (`localhost`, or the Tailscale name of the host) reaches every service. The wave that deploys a service also owns its `HTTPRoute`, so this wave holds only the Gateway.

Service-to-service (east-west) traffic does NOT go through this Gateway. In-cluster callers use Service DNS directly (e.g. `polaris.lakehouse-catalog.svc.cluster.local:8181`).

## Deployed Resources

```
Namespace: istio-ingress
├── platform-gateway        (Gateway, listener http :80, any hostname)
├── platform-gateway-istio  (Deployment + Service, created by istiod)
```

## Routes

| Path prefix | Backend | HTTPRoute (wave) | How the app serves under it |
|---|---|---|---|
| `/console` | `console:8080` in `lakehouse-control-plane` | `console` (`25-lakehouse-control-plane` chart) | the app's router basename and nginx are `/console` |
| `/kiali` | `kiali:20001` in `istio-system` | `kiali` (`23-kiali`) | `server.web_root: /kiali` |
| `/kafka-ui` | `kafka-ui:8080` in `kafka-ui` | `kafka-ui` (`23-kafka-ui`) | `SERVER_SERVLET_CONTEXT_PATH=/kafka-ui` |
| `/temporal` | `temporal-web:8080` in `temporal` | `temporal-web` (`21-temporal`) | `TEMPORAL_UI_PUBLIC_PATH=/temporal` |
| `/polaris` | `polaris:8181` in `lakehouse-catalog` | `polaris` (`21-polaris`) | the route rewrites `/polaris` to `/` (`URLRewrite` `ReplacePrefixMatch`), so `/polaris/api/catalog/...` reaches Polaris as `/api/catalog/...`; in-cluster clients keep calling `polaris:8181` directly |
| `/keycloak` | `keycloak:8080` in `identity` | `keycloak` (`13-identity`) | Keycloak's HTTP relative path is `/keycloak`; ungated |
| `/sso` | `oauth2-proxy:4180` in `identity` | `oauth2-proxy` (`13-identity`) | oauth2-proxy proxy prefix `/sso`; ungated |
| `/identity-gate-probe` | `oauth2-proxy:4180` in `identity` | `oauth2-proxy` (`13-identity`) | gated; oauth2-proxy answers its static 200; `13-identity/validate.sh` checks the gate on it |
| `/ui`, `/oauth2` | `trino:8080` in `lakehouse-query-engine` | `trino-ui` (`23-trino`) | no rewrite; the route sets `X-Forwarded-Proto/Host/Port` from the public origin and Trino runs with `http-server.process-forwarded=true`; `/oauth2/callback` is Trino's OAuth2 redirect URI |

Each app serves under its own prefix rather than the route stripping it, so the links and assets it generates carry the prefix. `/` has no route: a request that matches no prefix gets a 404 from Envoy. A new service picks an unused prefix; an app that cannot serve under a prefix would need `/`, and only one can.

## Which namespaces may attach routes

The listener admits `HTTPRoute`s only from namespaces labelled `retail-lakehouse.io/gateway-routes=allowed`. A wave that adds a route calls `gateway::allow_routes <namespace>` (`scripts/utils/gateway.sh`) before applying it, and its `validate.sh` calls `gateway::assert_routes_allowed`, `gateway::assert_route_accepted` and `gateway::curl <path>` (curl a path through the gateway).

The label is applied with server-side apply under the field manager `platform-gateway-routes`, and `namespace::apply_ambient` applies the ambient label under `namespace-ambient`, so the two never remove each other's label. Do not add either label with a client-side `kubectl apply` of a partial Namespace manifest: kubectl's client-side → server-side migration then hands every field to the new manager and drops the labels that manifest leaves out.

## Access

The `networking.istio.io/service-type: ClusterIP` annotation keeps the Service `ClusterIP` (a `LoadBalancer` stays `<pending>` on minikube). From a laptop:

```bash
kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse
```

Then browse `http://localhost:8591/console/`, `http://localhost:8591/kiali/` and so on; the local port is free to choose. Because routes match on path only, the same paths work through any proxy that forwards to that port, for example `tailscale serve --https=8591 http://127.0.0.1:8591` gives `https://<host>.<tailnet>.ts.net:8591/console/` on the tailnet. The apps emit relative or prefix-only redirects, so the scheme and port the browser used are kept.

The listener used to carry `hostname: "*.localhost"`. On a cluster where that field was set before server-side apply took over, no field manager owns it and `bootstrap.sh` cannot remove it; apply the Gateway once with the hostname and then without it (a fresh cluster is not affected).

## Deploy order

Wave 12, after istiod (the Gateway controller) and the Gateway API CRDs (wave 11). Routes attach from waves 21 and later, so each route's `validate.sh` can check it is `Accepted` and reachable.
