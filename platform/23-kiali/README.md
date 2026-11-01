# 23-kiali

Kiali (view-only, anonymous auth) in `istio-system`, served at `/kiali` on `platform-gateway`.
Metrics come from Prometheus (`http://prometheus-k8s.monitoring:9090`), which scrapes ztunnel through
the `ztunnel` PodMonitor in `12-ztunnel`.

## Version

Chart `kiali-server` 2.20.0 (Kiali v2.20.0). Istio is 1.26.8, and kiali.io's compatibility table lists
Istio 1.26 for Kiali 2.9 to 2.20, so 2.20 is the newest supported version. Override with `KIALI_VERSION`.

## Access

```bash
kubectl port-forward service/platform-gateway-istio 8080:80 --namespace istio-ingress --context retail-lakehouse
```

Browse `http://localhost:8080/kiali/`. The graph shows only traffic of namespaces labelled
`istio.io/dataplane-mode=ambient`.

## Gateway

`bootstrap.sh` re-applies `22-polaris-routes/gateway.yaml`, whose `allowedRoutes` includes `istio-system`.
