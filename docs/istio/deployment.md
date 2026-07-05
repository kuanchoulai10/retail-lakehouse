# Deploy Istio in Ambient Mode

Istio ambient mode replaces the traditional sidecar model with a shared per-node data plane (`ztunnel`) plus optional per-identity waypoint proxies. This project installs the ambient control plane, its data plane, and the Kubernetes Gateway API CRDs — no namespace is enrolled into the mesh yet. The end state is a cluster that can *become* meshed the moment a namespace gets the ambient label, and can route north-south HTTP traffic through `Gateway` and `HTTPRoute` resources.

The install spans six wave-11 and wave-12 directories under `platform/`. Every directory follows the project's `bootstrap.sh` + `validate.sh` + `values.yaml` + `README.md` convention; `tasks/apps.yml` runs them in dependency order, and each ArgoCD `Application` under `charts/app-of-apps/templates/` mirrors the same wave.

!!! info "為什麼選 ambient mode 而不是 sidecar"

    Sidecar mode 對 Strimzi Kafka broker、Kafka Connect worker 這種 stateful/StatefulSet 常常出事：iptables redirect 干擾 JMX、init container 順序爆掉、broker 遲遲不 ready。Ambient 把 L4 mTLS 移到每個 node 上一份 `ztunnel`，workload pod 不用改，Kafka/Debezium/Polaris 全都可以照原本方式跑。

    代價是 L7 policy（AuthorizationPolicy 針對 HTTP method/path）要另外部署 waypoint proxy。這次沒開，等真的需要時再加。

## Configure the Wave Layout

Ambient install has hard ordering constraints: CRDs must exist before `istiod`, and `istio-cni`/`ztunnel` need `istiod` running to fetch xDS config and workload certificates. The project encodes this as two waves rather than one because ArgoCD's `sync-wave` runs same-wave `Applications` in parallel.

| Wave | Directory | Chart / Source | Role |
|------|-----------|----------------|------|
| 11 | `platform/11-istio-base/` | `istio/base` @ 1.26.8 | CRDs and cluster roles for the Istio control plane |
| 11 | `platform/11-gateway-api-crds/` | `kubernetes-sigs/gateway-api` @ v1.3.0 standard channel | `Gateway`, `HTTPRoute`, `GatewayClass`, `GRPCRoute`, `ReferenceGrant` |
| 12 | `platform/12-istiod/` | `istio/istiod` @ 1.26.8, `profile=ambient` | Control plane: xDS server, CA, sidecar-injector webhook |
| 12 | `platform/12-istio-cni/` | `istio/cni` @ 1.26.8, `profile=ambient` | Per-node CNI plugin that redirects traffic into `ztunnel` |
| 12 | `platform/12-ztunnel/` | `istio/ztunnel` @ 1.26.8 | Per-node L4 proxy that terminates and originates HBONE-encrypted mTLS |

Wave 11 installs pure CRDs (no workloads), so both entries can run in parallel. Wave 12 has an implicit intra-wave order: `istiod` needs to be `Ready` before `istio-cni` and `ztunnel` can join, but ArgoCD does not guarantee ordering within a wave. `tasks/apps.yml` handles this explicitly by running `istiod`'s bootstrap and validate before the other two.

## Configure Version Pinning

Every bootstrap script pins `ISTIO_VERSION` as a bash default that can be overridden from the shell:

```bash title="platform/11-istio-base/bootstrap.sh"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"
```

The initial spec pinned `1.26.2`, which we later bumped to `1.26.8` after hitting a broken chart schema.

!!! warning "Istio 1.26.2 `istio/gateway` chart schema is broken"

    In 1.26.2 the `istio/gateway` chart ships a `values.schema.json` that rejects its own default `_internal_defaults_do_not_set` block. Any `helm install istio-ingressgateway istio/gateway --version 1.26.2` fails schema validation before it even touches the cluster.

    `1.26.8` fixes it. Patch releases within the same minor are drop-in for Istio (they promise no config-breaking changes in patch). We bumped every chart to 1.26.8, not just the gateway one, to keep versions consistent.

Gateway API CRDs are pinned separately in `platform/11-gateway-api-crds/bootstrap.sh`:

```bash title="platform/11-gateway-api-crds/bootstrap.sh"
GATEWAY_API_VERSION="${GATEWAY_API_VERSION:-v1.3.0}"
```

The standard channel is what the Istio ambient docs recommend and covers everything this project uses (`Gateway`, `HTTPRoute`, `GatewayClass`, `ReferenceGrant`, `GRPCRoute`). The experimental channel adds `TCPRoute`, `UDPRoute`, `TLSRoute`, mesh-related resources — none of which we need.

## Configure Ambient Profile and Platform Flags

Each Helm chart takes a small set of ambient- and minikube-specific overrides. The values files stay minimal — only what the upstream defaults get wrong for our environment.

`istiod` is the largest one:

```yaml title="platform/12-istiod/values.yaml"
profile: ambient

global:
  platform: minikube

meshConfig:
  accessLogFile: /dev/stdout

pilot:
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
```

`profile: ambient` is the master switch — it turns off sidecar injection defaults and enables the ambient-specific reconcilers inside `istiod`. `global.platform=minikube` is a platform prerequisite documented by Istio itself: minikube's docker driver uses non-standard bind-mount paths for `/var/run` and `/opt/cni`, and both `istio-cni` and `ztunnel` need this flag to write their CNI config into paths the kubelet actually reads. `meshConfig.accessLogFile: /dev/stdout` sends Envoy access logs to pod stdout so `kubectl logs` shows them without extra configuration.

`istio-cni` and `ztunnel` each take a two-line values file:

```yaml title="platform/12-istio-cni/values.yaml"
profile: ambient
global:
  platform: minikube
```

```yaml title="platform/12-ztunnel/values.yaml"
global:
  platform: minikube
```

`ztunnel` deliberately does not take `profile: ambient` — the chart is ambient-only (there is no sidecar variant), and adding the flag triggers an unknown-value warning.

## Configure the Gateway API CRDs

The CRDs install by direct `kubectl apply` against the upstream release YAML, not through a Helm chart:

```bash title="platform/11-gateway-api-crds/bootstrap.sh"
kubectl apply --server-side \
  -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml" \
  --context "${KUBE_CONTEXT}"
```

`--server-side` is required because the Gateway API CRDs are large (~600KB) and hit the `Last-Applied-Configuration` annotation limit under client-side apply. The ArgoCD template mirrors this by vendoring the manifest under `platform/11-gateway-api-crds/manifests/standard-install-v1.3.0.yaml` and syncing that directory with `syncOptions: ServerSideApply=true`.

## Configure Namespace Isolation

`istio-system` holds the control plane (`istiod`, `istio-cni-node` DaemonSet, `ztunnel` DaemonSet). It is created by `platform/11-istio-base/bootstrap.sh`'s `--create-namespace` flag.

`istio-ingress` is a separate namespace for user-facing Gateway resources. It exists so RBAC and NetworkPolicy on the control plane can be tighter than what user-facing gateways need — a convention Istio's own docs adopted in 1.6 after complaints about mixing tenant traffic with control-plane pods in `istio-system`.

!!! info "Why not merge `istio-ingress` into `istio-system`"

    You *can* — early Istio installs put ingress gateways in `istio-system`. The split lets you write `NetworkPolicy` that isolates the control plane from tenant traffic, and lets platform team and application team own separate namespaces with separate RBAC. On a single-tenant dev cluster the isolation is theatre, but the convention is what any Istio-familiar hire will expect.

The auto-spawn behaviour of the Istio Gateway API controller means `istio-ingress` also hosts the auto-created Envoy `Deployment` and `Service` for each `Gateway` resource. This is covered in [Gateway API Routing Design](routing.md).

## Verify the Install

After all six directories have bootstrapped and validated, five pods should be running across two namespaces:

```
istio-system:  istiod-*, istio-cni-node-*, ztunnel-*
istio-ingress: (empty until the first Gateway resource is applied)
```

Sanity check the CRDs and GatewayClass are in place:

```bash
kubectl get crd --context retail-lakehouse | grep -E "istio|gateway.networking"
kubectl get gatewayclass --context retail-lakehouse
```

You should see 14 Istio CRDs, 5 Gateway API CRDs, and three GatewayClasses: `istio` (auto-managed Envoy per Gateway), `istio-remote` (for multi-cluster), and `istio-waypoint` (for L7 waypoint proxies). The `istio` GatewayClass is the one you'll reference from `Gateway` resources.

No workload pod has an `istio-proxy` sidecar container:

```bash
kubectl get pods -A -o yaml --context retail-lakehouse | grep -c "name: istio-proxy"
```

Should return `0`. Ambient enrollment is opt-in — a namespace only joins the mesh once labelled `istio.io/dataplane-mode=ambient`. This project does not label any namespace yet; ambient stays inert until an explicit follow-up.

## References

- [Istio Ambient Mode Install (Helm)](https://istio.io/latest/docs/ambient/install/helm/) — the canonical step-by-step for the five charts
- [Istio Ambient Platform Prerequisites](https://istio.io/latest/docs/ambient/install/platform-prerequisites/) — where `global.platform=minikube` is documented
- [Istio Ambient Mode Overview](https://istio.io/latest/docs/ambient/overview/) — architecture rationale for `ztunnel` + waypoint split
- [Kubernetes Gateway API v1.3.0 release](https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.3.0) — release notes and manifests
- [Gateway API standard vs experimental channel](https://gateway-api.sigs.k8s.io/concepts/versioning/#release-channels) — why we pin standard
- [Istio Helm values reference](https://artifacthub.io/packages/helm/istio-official/istiod) — full override surface for each chart
