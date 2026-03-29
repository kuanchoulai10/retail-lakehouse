# cert-manager

Deploys cert-manager, a Kubernetes-native certificate management controller. cert-manager automates the issuance and renewal of TLS certificates from various sources. In this stack, it manages TLS certificates for KEDA's admission webhooks.

## Deployed Resources

```
Namespace: cert-manager
├── cert-manager                         (Deployment)
├── cert-manager-webhook                 (Deployment)
└── cert-manager-cainjector              (Deployment)
```

## Namespaces

- `cert-manager`

## Pods

| Pod | Purpose |
|-----|---------|
| `cert-manager` | Issues and renews certificates |
| `cert-manager-webhook` | Validates Certificate and Issuer resources |
| `cert-manager-cainjector` | Injects CA bundles into webhook configurations |

## CRDs

| CRD | Purpose |
|-----|---------|
| `certificates.cert-manager.io` | Requests a signed TLS certificate |
| `certificaterequests.cert-manager.io` | Tracks a single certificate signing request |
| `issuers.cert-manager.io` | Namespace-scoped certificate issuer |
| `clusterissuers.cert-manager.io` | Cluster-scoped certificate issuer |
| `orders.acme.cert-manager.io` | Tracks an ACME order |
| `challenges.acme.cert-manager.io` | Tracks an ACME challenge |
