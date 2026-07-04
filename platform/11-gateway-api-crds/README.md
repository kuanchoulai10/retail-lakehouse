# gateway-api-crds

Installs the Kubernetes Gateway API standard-channel CRDs via `kubectl apply --server-side` against the upstream release YAML. Pinned to `v1.3.0`, standard channel — GA resources only (no experimental TCPRoute/UDPRoute/TLSRoute).

## Deployed Resources

CRDs only, no namespace, no workloads.

## CRDs

| CRD | Purpose |
|-----|---------|
| `gatewayclasses.gateway.networking.k8s.io` | Declares a controller implementation (e.g. Istio) |
| `gateways.gateway.networking.k8s.io` | Instantiates an inbound listener bound to a GatewayClass |
| `httproutes.gateway.networking.k8s.io` | HTTP L7 routing rules attached to a Gateway |
| `grpcroutes.gateway.networking.k8s.io` | gRPC routing rules attached to a Gateway |
| `referencegrants.gateway.networking.k8s.io` | Cross-namespace reference authorization |
