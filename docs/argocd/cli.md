# Argo CD CLI

## Install the CLI

Follow the [official installation guide](https://argo-cd.readthedocs.io/en/stable/cli_installation/) for your platform.

## Get the Initial Admin Password

The initial admin password is stored in a Kubernetes secret. Retrieve it using `kubectl`:

```bash
kubectl --context=mini get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath='{.data.password}' | base64 -d && echo
```

## Port-forward the Argo CD Server

Since `argocd-server` is a `ClusterIP` service, expose it locally before using the CLI:

```bash
kubectl --context=mini port-forward svc/argocd-server -n argocd 8080:443 &
```

## Log In

```bash
argocd login localhost:8080 \
  --username admin \
  --password <password> \
  --insecure
```

## Verify Cluster Connection

```bash
argocd cluster list
```

Expected output:

```
SERVER                          NAME        VERSION  STATUS      MESSAGE  PROJECT
https://kubernetes.default.svc  in-cluster  1.33     Successful
```

`in-cluster` is the target Kubernetes cluster managed by Argo CD.
