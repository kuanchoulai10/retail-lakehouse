# ArgoCD Health Checks

Patches the `argocd-cm` ConfigMap to register a custom health check for `argoproj.io/Application` resources. Without this patch, ArgoCD cannot evaluate the health of child Applications when using the app-of-apps pattern, causing parent Applications to remain in a `Progressing` state indefinitely.

## Deployed Resources

```
Namespace: argocd
└── argocd-cm   (ConfigMap, patched)
```

## Namespaces

- `argocd` (pre-existing, created by `00-argocd`)
