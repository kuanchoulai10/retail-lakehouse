# Argo CD Deployment

First, deploy Argo CD to your Kubernetes cluster using the following commands:

```bash
export ARGOCD_VERSION=v3.1.7
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml
```

It will install all the necessary components for Argo CD in the `argocd` namespace.

To retrieve the initial admin password for Argo CD, use the following command:

```bash
argocd admin initial-password -n argocd
```

To access the Argo CD web UI, you can port-forward the Argo CD server service to your local machine:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Then, open your web browser and navigate to:

```
https://localhost:8080
```

To log in, use the username `admin` and the initial password retrieved earlier.