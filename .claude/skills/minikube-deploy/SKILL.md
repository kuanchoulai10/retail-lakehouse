---
name: minikube-deploy
description: Build Docker images, load into Minikube, and deploy to the cluster. Use this skill whenever the user wants to build and deploy an image to Minikube, redeploy after code changes, do a dev iteration cycle (build-load-deploy), clean up old images, or troubleshoot image-related issues in Minikube. Also trigger when user says "deploy", "build image", "push to minikube", "redeploy", or mentions updating a running service in the cluster.
---

# Minikube Build-Load-Deploy

This skill standardizes the cycle of building a Docker image locally, loading it into Minikube, cleaning up old images, and deploying/redeploying to the cluster.

## Environment

- Minikube profile: `lakehouse-demo`
- Docker runtime: Colima (Docker runs inside a VM — `localhost` from Docker ≠ host `localhost`)
- Image loading: `minikube image load` (direct load into containerd, no registry networking needed)
- Image naming: `localhost:5001/<name>:latest` (convention only — images are loaded directly, not pulled from a registry)
- `imagePullPolicy: Never` in all manifests (prevents K8s from trying to pull from a registry)
- K8s manifests live in numbered directories (e.g., `25-table-maintenance/`)

### Why `minikube image load` instead of registry push?

Docker runs inside Colima VM. `kubectl port-forward` binds to the host network. When Docker tries to `push` to `localhost:5001`, it resolves to the Colima VM's localhost — not the host where port-forward is listening. `minikube image load` bypasses this entirely by streaming the image directly into Minikube's container runtime.

## Known Images

| Image Name | Dockerfile | Build Context | Deploy Manifest | Deploy Kind |
|-----------|-----------|--------------|----------------|------------|
| `table-maintenance-jobs` | `src/table-maintenance/jobs/Dockerfile` | `src/table-maintenance/jobs/` | `25-table-maintenance/sparkapplication-rewrite-data-files.yaml` | SparkApplication |
| `table-maintenance-backend` | `src/table-maintenance/backend/Dockerfile` | `src/table-maintenance/backend/` | `25-table-maintenance/backend-deployment.yaml` | Deployment + Service |

When the user asks to deploy something not in this table, ask them for the Dockerfile path, build context, and deploy manifest path. Then add it to this table for future reference.

## Workflow

Execute these steps in order. If any step fails, stop and diagnose before continuing.

### Step 1: Clean Old Images

Remove old images to free space before building new ones.

**Remove from Minikube's container runtime:**
```bash
minikube image rm localhost:5001/<IMAGE_NAME>:latest -p lakehouse-demo 2>/dev/null || true
```

**Remove from local Docker:**
```bash
docker rmi localhost:5001/<IMAGE_NAME>:latest 2>/dev/null || true
```

### Step 2: Build Image

```bash
docker build -t localhost:5001/<IMAGE_NAME>:latest <BUILD_CONTEXT>
```

Replace `<BUILD_CONTEXT>` with the absolute path from the Known Images table. If the Dockerfile is not at the root of the build context, add `-f <DOCKERFILE_PATH>`.

### Step 3: Load into Minikube

```bash
minikube image load localhost:5001/<IMAGE_NAME>:latest -p lakehouse-demo
```

Verify the image is loaded:
```bash
minikube image ls -p lakehouse-demo 2>/dev/null | grep <IMAGE_NAME>
```

### Step 4: Deploy

The deploy strategy depends on the resource kind:

**For Deployment (e.g., backend):**
```bash
kubectl apply -f <MANIFEST_PATH>
# Force pods to recreate with the new image
kubectl rollout restart deployment/<DEPLOYMENT_NAME> -n default
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n default --timeout=60s
```

**For SparkApplication (e.g., jobs):**

SparkApplications are one-shot — delete the old one before resubmitting:
```bash
kubectl delete sparkapplication/<APP_NAME> -n default --ignore-not-found
kubectl apply -f <MANIFEST_PATH>
```

Then show the user how to monitor:
```bash
kubectl get sparkapplication/<APP_NAME> -n default -w
kubectl logs -n default -l spark-role=driver,spark-app-name=<APP_NAME> -f
```

### Step 5: Verify

After deploy, confirm the workload is healthy:

**For Deployment:**
```bash
kubectl get pods -l app=<DEPLOYMENT_NAME> -n default
```

**For SparkApplication:**
```bash
kubectl get sparkapplication/<APP_NAME> -n default
```

## Bulk Cleanup

If the user wants to free up space across all images:

```bash
# List images in minikube
minikube image ls -p lakehouse-demo 2>/dev/null | grep localhost

# Prune dangling docker images locally
docker image prune -f

# Check minikube disk usage
minikube ssh -p lakehouse-demo -- df -h /
```

## Troubleshooting

If pods show `ErrImageNeverPull` or `ImagePullBackOff`:

1. **Image not loaded** → re-run `minikube image load`
2. **imagePullPolicy wrong** → must be `Never` for locally-loaded images
3. **Image name mismatch** → compare `minikube image ls` output with manifest's `image:` field exactly
4. **Disk full** → run bulk cleanup above

For deeper diagnosis, see `docs/troubleshooting-minikube-image-pull.md` in this repo.
