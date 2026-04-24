---
name: minikube-deploy
description: Build Docker images, load into Minikube, and deploy to the cluster. Use this skill whenever the user wants to build and deploy an image to Minikube, redeploy after code changes, do a dev iteration cycle (build-load-deploy), clean up old images, or troubleshoot image-related issues in Minikube. Also trigger when user says "deploy", "build image", "push to minikube", "redeploy", or mentions updating a running service in the cluster.
---

# Minikube Build-Load-Deploy

This skill standardizes the cycle of building a Docker image locally, loading it into Minikube, cleaning up old images, and deploying/redeploying to the cluster.

## Environment

- Minikube profile: `lakehouse-demo`
- Docker runtime: Colima (Docker runs inside a VM — `localhost` from Docker ≠ host `localhost`)
- Image naming: `localhost:5001/<name>:<tag>` (convention only — images are loaded directly, not pulled from a registry)
- `imagePullPolicy: Never` in all manifests (prevents K8s from trying to pull from a registry)
- K8s manifests live in numbered directories (e.g., `25-table-maintenance/`)

### Why `minikube image load` instead of registry push?

Docker runs inside Colima VM. `kubectl port-forward` binds to the host network. When Docker tries to `push` to `localhost:5001`, it resolves to the Colima VM's localhost — not the host where port-forward is listening. `minikube image load` bypasses this entirely by streaming the image directly into Minikube's container runtime.

## Known Images

| Image Name | Dockerfile | Build Context | Deploy Manifest | Deploy Kind |
|-----------|-----------|--------------|----------------|------------|
| `table-maintenance-spark` | `src/table-maintenance/runtime/spark/Dockerfile` | `src/table-maintenance/runtime/spark/` | `25-table-maintenance/sparkapplication-rewrite-data-files.yaml` | SparkApplication |
| `table-maintenance-backend` | `src/table-maintenance/backend/Dockerfile` | `src/table-maintenance/backend/` | `25-tbl-maint-bcknd/backend-deployment.yaml` | Deployment + Service |
| `table-maintenance-scheduler` | `src/table-maintenance/scheduler/Dockerfile` | `src/table-maintenance/` | `25-tbl-maint-schdlr/scheduler-deployment.yaml` | Deployment |

When the user asks to deploy something not in this table, ask them for the Dockerfile path, build context, and deploy manifest path. Then add it to this table for future reference.

## Workflow

Execute these steps in order. If any step fails, stop and diagnose before continuing.

### Step 1: Generate a Unique Image Tag and Record the Previous Tag

Never use `:latest` for deploy iterations. The `latest` tag causes caching issues where `minikube image load` silently keeps the old image. Use a unique tag for every build so K8s is forced to pull the new image.

Read the current image tag from the manifest so you can clean it up later:
```bash
OLD_TAG=$(grep 'image:.*<IMAGE_NAME>' <MANIFEST_PATH> | sed 's/.*://')
```

Generate a new tag based on timestamp:
```bash
TAG=$(date +%Y%m%d-%H%M%S)
```

Example: `localhost:5001/table-maintenance-backend:20260421-213000`

### Step 2: Build Image

```bash
docker build -t localhost:5001/<IMAGE_NAME>:$TAG <BUILD_CONTEXT>
```

Replace `<BUILD_CONTEXT>` with the absolute path from the Known Images table. If the Dockerfile is not at the root of the build context, add `-f <DOCKERFILE_PATH>`.

**After build completes, verify the image has the expected files:**
```bash
docker run --rm localhost:5001/<IMAGE_NAME>:$TAG ls /app/
```

This catches Dockerfile issues (missing COPY, wrong build context) before loading into Minikube.

### Step 3: Load into Minikube

Use `docker save` + `ctr import` for reliable image loading. `minikube image load` has caching issues where it can silently keep old image layers even with a new tag.

```bash
docker save localhost:5001/<IMAGE_NAME>:$TAG -o /tmp/<IMAGE_NAME>.tar
minikube cp /tmp/<IMAGE_NAME>.tar lakehouse-demo:/tmp/<IMAGE_NAME>.tar -p lakehouse-demo
minikube ssh -p lakehouse-demo -- "sudo ctr -n k8s.io images import /tmp/<IMAGE_NAME>.tar && sudo rm -f /tmp/<IMAGE_NAME>.tar"
rm /tmp/<IMAGE_NAME>.tar
```

Also run `minikube image load` to ensure crictl sees the tag (ctr import alone sometimes isn't enough for crictl):
```bash
minikube image load localhost:5001/<IMAGE_NAME>:$TAG -p lakehouse-demo
```

Verify the image is loaded:
```bash
minikube ssh -p lakehouse-demo -- "sudo crictl images | grep <IMAGE_NAME>"
```

### Step 4: Update Manifest and Deploy

Update the image tag in the manifest file before applying. Do not rely on `rollout restart` with the same tag — K8s won't detect a change.

1. Update the `image:` field in the manifest to use the new tag
2. Apply and wait:

**For Deployment (e.g., backend):**
```bash
kubectl apply -f <MANIFEST_PATH>
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n default --timeout=90s
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

After deploy, confirm the workload is healthy and running the correct image:

**For Deployment:**
```bash
# Check pod status
kubectl get pods -l app=<DEPLOYMENT_NAME> -n default

# Verify the pod is running the new image (check the tag matches)
kubectl get pod -l app=<DEPLOYMENT_NAME> -n default -o jsonpath='{.items[0].spec.containers[0].image}'

# Verify files inside the running pod
kubectl exec $(kubectl get pods -l app=<DEPLOYMENT_NAME> -n default -o jsonpath='{.items[0].metadata.name}') -n default -- ls /app/
```

**For SparkApplication:**
```bash
kubectl get sparkapplication/<APP_NAME> -n default
```

### Step 6: Clean Up Previous Image

After the new pod is verified running, remove the old image from both local Docker and Minikube to prevent disk bloat. Minikube disk space is limited — skipping cleanup will eventually cause deploy failures.

```bash
# Remove old image from local Docker
docker rmi localhost:5001/<IMAGE_NAME>:$OLD_TAG 2>/dev/null || true
docker image prune -f

# Remove old image from Minikube (both ctr and crictl layers)
minikube ssh -p lakehouse-demo -- "sudo ctr -n k8s.io images rm localhost:5001/<IMAGE_NAME>:$OLD_TAG" 2>/dev/null || true
minikube ssh -p lakehouse-demo -- "sudo ctr -n k8s.io content prune references" 2>/dev/null || true
```

Verify only the new tag remains:
```bash
minikube ssh -p lakehouse-demo -- "sudo crictl images | grep <IMAGE_NAME>"
```

### Step 7: Smoke Test

If the deployed service has an HTTP endpoint, port-forward and test it:

```bash
kubectl port-forward svc/<SERVICE_NAME> <PORT>:<PORT> -n default &
sleep 3
curl -s http://localhost:<PORT>/health
```

## Bulk Cleanup

If the user wants to free up space across all images:

```bash
# List images in minikube
minikube ssh -p lakehouse-demo -- "sudo crictl images" | grep localhost

# Prune dangling docker images locally
docker image prune -f

# Check minikube disk usage
minikube ssh -p lakehouse-demo -- df -h /
```

## Troubleshooting

### ErrImageNeverPull or ImagePullBackOff

1. **Image not loaded** — verify with `crictl images`, not just `minikube image ls`. If missing, re-run the `docker save` + `ctr import` flow.
2. **imagePullPolicy wrong** — must be `Never` for locally-loaded images
3. **Image name/tag mismatch** — compare `crictl images` output with manifest's `image:` field exactly (including tag)
4. **Disk full** — run bulk cleanup above

### Image loaded but pod has old files

This is the most common issue. Causes:
1. **Used `:latest` tag** — minikube caches aggressively. Solution: always use unique tags.
2. **`minikube image load` cached old layers** — Solution: use `docker save` + `ctr import` instead.
3. **Pod using old image** — verify with: `kubectl get pod <POD> -o jsonpath='{.status.containerStatuses[0].imageID}'` and compare to local `docker inspect --format '{{.Id}}'`.

### Cross-namespace service connection failures

If the deployed app can't reach services in other namespaces (e.g., `Failed to resolve 'polaris'`), use the FQDN: `<service>.<namespace>.svc.cluster.local`. Configure via environment variables in the deployment manifest.

For deeper diagnosis, see `docs/troubleshooting-minikube-image-pull.md` in this repo.
