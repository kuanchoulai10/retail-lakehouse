# ArgoCD

Installs ArgoCD v3.1.7 into the `argocd` namespace by applying the upstream install manifest. ArgoCD is the GitOps continuous delivery controller that reconciles all subsequent components in this stack from Git.

## Deployed Resources

```
Namespace: argocd
├── argocd-server                      (Deployment)
├── argocd-repo-server                 (Deployment)
├── argocd-applicationset-controller   (Deployment)
├── argocd-notifications-controller    (Deployment)
├── argocd-dex-server                  (Deployment)
├── argocd-redis                       (Deployment)
└── argocd-application-controller      (StatefulSet)
```

## Namespaces

- `argocd`

## Pods

| Pod | Purpose |
|-----|---------|
| `argocd-server` | Serves the ArgoCD API and UI |
| `argocd-repo-server` | Clones Git repos and renders manifests |
| `argocd-applicationset-controller` | Manages ApplicationSet resources |
| `argocd-notifications-controller` | Sends deployment notifications |
| `argocd-dex-server` | Handles SSO and OIDC authentication |
| `argocd-redis` | Caches repository and application state |
| `argocd-application-controller` | Reconciles Application resources against the cluster |

## CRDs

| CRD | Purpose |
|-----|---------|
| `applications.argoproj.io` | Declares a GitOps-managed application |
| `applicationsets.argoproj.io` | Generates Applications from a template and generator |
| `appprojects.argoproj.io` | Scopes access and destination rules for Applications |
