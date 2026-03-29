# ArgoCD Root Application

Deploys the root ArgoCD Application using the app-of-apps pattern. This single Application points ArgoCD at the `charts/app-of-apps` Helm chart in the `retail-lakehouse` Git repository. ArgoCD renders that chart and creates child Applications for every other component in the stack, with automated sync, self-healing, and pruning enabled.

## Deployed Resources

```
Namespace: argocd
└── root-app   (Application)
```

## Namespaces

- `argocd` (pre-existing, created by `00-argocd`)
