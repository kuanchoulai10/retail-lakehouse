# platform-gateway

The single north-south entry point of the platform: one Gateway API `Gateway` in `istio-ingress`, backed by an Envoy that Istio creates for it. Each web UI or API gets its own hostname under `*.localhost`. The wave that deploys a service also owns its `HTTPRoute`, so this wave holds only the Gateway.

Service-to-service (east-west) traffic does NOT go through this Gateway. In-cluster callers use Service DNS directly (e.g. `polaris.lakehouse-catalog.svc.cluster.local:8181`).

## Deployed Resources

```
Namespace: istio-ingress
├── platform-gateway        (Gateway, listener http :80, hostname *.localhost)
├── platform-gateway-istio  (Deployment + Service, created by istiod)
```

## Routes

| Hostname | Backend | HTTPRoute (wave) |
|---|---|---|
| `console.localhost` | `console:8080` in `lakehouse-control-plane` | `console` (`25-lakehouse-control-plane` chart) |
| `kiali.localhost` | `kiali:20001` in `istio-system` | `kiali` (`23-kiali`) |
| `kafka-ui.localhost` | `kafka-ui:8080` in `kafka-ui` | `kafka-ui` (`23-kafka-ui`) |
| `temporal.localhost` | `temporal-web:8080` in `temporal` | `temporal-web` (`21-temporal`) |
| `polaris.localhost` | `polaris:8181` in `lakehouse-catalog` | `polaris` (`21-polaris`) |

A request whose `Host` matches no route gets a 404 from Envoy.

## Which namespaces may attach routes

The listener admits `HTTPRoute`s only from namespaces labelled `platform-gateway/routes=allowed`. A wave that adds a route calls `gateway::allow_routes <namespace>` (`scripts/utils/gateway.sh`) before applying it, and its `validate.sh` calls `gateway::assert_routes_allowed`, `gateway::assert_route_accepted` and `gateway::curl` (curl through the gateway with a given `Host`).

The label is applied with server-side apply under the field manager `platform-gateway-routes`, and `namespace::apply_ambient` applies the ambient label under `namespace-ambient`, so the two never remove each other's label. Do not add either label with a client-side `kubectl apply` of a partial Namespace manifest: kubectl's client-side → server-side migration then hands every field to the new manager and drops the labels that manifest leaves out.

## Access

The `networking.istio.io/service-type: ClusterIP` annotation keeps the Service `ClusterIP` (a `LoadBalancer` stays `<pending>` on minikube). From a laptop:

```bash
kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse
```

Then browse `http://console.localhost:8591/`, `http://kiali.localhost:8591/` and so on. Chrome, Firefox and curl resolve every `*.localhost` name to the loopback address without any `/etc/hosts` entry; Safari may not. Istio matches the hostname with any port, so the local port is free to choose.

## Deploy order

Wave 12, after istiod (the Gateway controller) and the Gateway API CRDs (wave 11). Routes attach from waves 21 and later, so each route's `validate.sh` can check it is `Accepted` and reachable.
