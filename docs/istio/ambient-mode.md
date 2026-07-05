# How Istio Ambient Mode Works

Istio ambient mode is a service mesh data plane that puts the L4 mTLS proxy on the *node*, not in the *pod*. Workload pods run unmodified: no sidecar container, no init container mangling iptables, no rolling restarts when the mesh upgrades. In exchange the mesh gives up cheap per-pod L7 policy. Any HTTP-aware behaviour (path-based authorization, header manipulation, per-route retries) requires opting the workload into a second layer called a **waypoint proxy**. Ambient's central bet is that most workloads only need L4 mTLS and identity, and shouldn't pay the sidecar tax to get it.

## Architecture Components

`istiod`
: The control plane. Same binary and role as in sidecar mode: it watches Kubernetes resources, compiles them into Envoy xDS config, issues workload certificates from an internal CA, and pushes config to every data plane process that connects. In ambient mode `istiod` additionally reconciles Kubernetes Gateway API resources into the auto-spawned Envoy Deployments and Services that back them.

`istio-cni` node agent
: A DaemonSet running one privileged pod per node. It installs a CNI plugin binary into `/opt/cni/bin` on the host and writes CNI config into `/etc/cni/net.d`. Every time a new pod starts on the node, the CNI plugin runs, checks whether the pod's namespace is enrolled in ambient (`istio.io/dataplane-mode=ambient` label), and if so programs iptables rules that redirect the pod's outbound traffic to the node's `ztunnel`. It replaces the init-container-with-NET_ADMIN pattern that sidecar mode used, which required each workload pod to briefly hold privileged capabilities.

`ztunnel`
: The ambient data plane. One DaemonSet pod per node, written in Rust for a low memory footprint (~40 MB per node vs. Envoy's 50-100 MB per pod in sidecar mode). It terminates and originates mTLS on behalf of every ambient-enrolled workload on its node. The name is informally a contraction of "zero-trust tunnel"; the Istio team never officially expanded it. `ztunnel` is deliberately L4-only: it moves bytes between identities, but it does not parse HTTP, so it cannot enforce `HTTPRoute`-level policies. Any L7 concern goes to a waypoint.

Waypoint proxy
: An optional Envoy Deployment sitting between a source and one or more destinations. Deployed via a `Gateway` resource with `gatewayClassName: istio-waypoint` and attached to a Service or ServiceAccount by an annotation. Unlike sidecars, a waypoint runs *outside* the workload pod and serves *multiple* pods that share the same identity. When present, `ztunnel` on the source node HBONE-tunnels traffic to the waypoint instead of directly to the destination node, so L7 policies (path-based authz, RBAC by header, retry policies) can execute there.

HBONE
: HTTP-Based Overlay Network Encapsulation. The tunnel protocol `ztunnel` uses to move traffic between nodes. Concretely, a mutually authenticated TLS connection carrying HTTP/2 `CONNECT` frames on port 15008. The inner payload is the workload's original L4 stream. The HTTP framing is a deliberate choice; it lets L7-aware components (waypoints, observability tools) inspect metadata like source identity and destination service without needing a bespoke tunnel protocol.

## Core Concepts

### Sidecar Mode's Problems Motivated Ambient

**Sidecar mode injected an Envoy container into every pod that joined the mesh.** The Envoy shared the pod's network namespace, and iptables (programmed by an init container) redirected all inbound and outbound traffic through it. That gave you L4 and L7 in one shot: mTLS, authz, retries, observability, all at the pod level.

Three problems built up over the years. First, **the tax was per-pod**: 50-100 MB of RAM and a fraction of a CPU core per workload pod, whether the workload needed L7 features or not. On clusters with tens of thousands of pods this dominated resource budgets. Second, **StatefulSet and DaemonSet workloads suffered**: Strimzi Kafka brokers, Kafka Connect workers, Prometheus, and CNI plugins all interact with the network stack in ways that iptables redirect broke. JMX, headless services, and host-network pods all needed manual `sidecar.istio.io/inject=false` opt-outs. Third, **upgrades required rolling every workload pod** because the sidecar binary lived inside the pod. Fleets stalled on release cadence.

Ambient's design goal is to keep mTLS and identity for free, decouple the L7 upgrade cycle from workload releases, and let L7-heavy tenants opt in on top rather than everyone opting out.

### The Two-Layer Data Plane Splits L4 from L7

The single most important shift is **splitting the data plane into a lightweight L4 layer that runs everywhere and a heavier L7 layer that runs only where needed**. `ztunnel` is the L4 layer: cheap, always-on, node-scoped, handles mTLS and identity. Waypoint proxies are the L7 layer: full Envoy, per-identity, optional.

This decomposition is why ambient can be dramatically cheaper than sidecar for the median workload. A namespace that only needs "pod-to-pod traffic should be encrypted and I want to know which service talked to which" pays for `ztunnel` (one per node, amortised across every pod on the node) and nothing else. Only when the namespace needs `AuthorizationPolicy` rules on HTTP path or method does it opt into a waypoint.

### Zero Trust Falls Out of the Layer Split

Because `ztunnel` handles identity at the node level, **every packet leaving an ambient-enrolled pod is stamped with the source ServiceAccount's identity via mTLS**. The destination `ztunnel` (or waypoint, if present) verifies the identity before decrypting. There is no way for one ambient pod to talk to another ambient pod without both sides agreeing on identities, and identity is bound to Kubernetes ServiceAccount, not IP.

This is the "zero trust" property in "zero trust tunnel". It holds even without any `AuthorizationPolicy` declared; the baseline is authenticated encryption. `AuthorizationPolicy` narrows what identities can reach what services; it doesn't have to establish trust from scratch.

### Ambient Is Opt-In Per Namespace

Ambient never turns on for a namespace automatically. Enrollment is triggered by a label on the namespace:

```yaml
metadata:
  labels:
    istio.io/dataplane-mode: ambient
```

Once labelled, the `istio-cni` plugin will program iptables redirect rules for any pod scheduled into that namespace. Existing pods do not get redirected retroactively; they must be recreated. Removing the label reverses the behaviour on next pod creation.

This project does not label any namespace yet. The mesh infrastructure is installed and idle. Ambient turns on the moment a namespace opts in.

## Behind the Scenes

### The Path of a Packet (L4 Only)

Pod A in namespace `alpha` (ambient-enrolled) sends a TCP connection to `service-b.beta.svc.cluster.local`. The path:

1. Pod A's kernel sends the packet as normal. It has no idea a mesh exists.
2. The `istio-cni` iptables rules on Node 1 (Pod A's node) catch the outbound packet on its way through the netfilter chain, redirect it to the local `ztunnel` DaemonSet pod on port 15001.
3. `ztunnel` on Node 1 receives the connection. It resolves `service-b`'s ClusterIP to a target Pod B on Node 2 via the Kubernetes Service, and it looks up Pod A's ServiceAccount to determine the source identity.
4. `ztunnel` on Node 1 opens an HBONE tunnel to `ztunnel` on Node 2. The tunnel is a mutually authenticated TLS connection on port 15008 carrying an HTTP/2 CONNECT frame that specifies "connect me to Pod B, and here is my identity".
5. `ztunnel` on Node 2 verifies the source identity against any `PeerAuthentication` or `AuthorizationPolicy` in play. If allowed, it opens a plain TCP connection to Pod B on the target port.
6. Bytes flow: Pod A to Node 1 kernel, Node 1 kernel to Node 1 `ztunnel`, Node 1 `ztunnel` through the HBONE tunnel to Node 2 `ztunnel`, Node 2 `ztunnel` to Pod B. Pod B sees the connection as coming from Node 2 `ztunnel`'s pod IP, but the identity header inside HBONE tells `ztunnel` and observability tools who the real source is.

If a waypoint is attached to Pod B's Service, step 5 changes: Node 2 `ztunnel` HBONE-tunnels to the waypoint instead, which decrypts, runs L7 rules, and forwards to Pod B. Waypoints can add or drop L7 policy without modifying `ztunnel`.

### `istiod` Distributes Config via xDS

`ztunnel` and every waypoint proxy connect to `istiod:15012` and speak Envoy's xDS protocol. `istiod` sends listener configs (LDS), route configs (RDS), cluster configs (CDS), and endpoint configs (EDS). For `ztunnel` this is a subset; it only cares about workload identities, node-to-node routes, and authorization policies. For waypoints it is a fuller Envoy config including HTTP route matchers.

The same `istiod` process serves both. There is no separate ambient control plane. Sidecar-mode workloads and ambient-mode workloads can coexist in the same cluster served by the same `istiod`.

### The `ambient` Profile Toggles Reconcilers

Istio's Helm charts accept a `profile` value that pre-configures many sub-values consistently. `profile: ambient` on `istiod` turns on the ambient-mode reconcilers, changes the default `PeerAuthentication` behaviour, and configures the sidecar injector to *not* inject for ambient-labelled namespaces. `profile: ambient` on `istio-cni` tells the CNI plugin to program ambient-mode iptables redirects instead of sidecar-mode ones.

`ztunnel` does not take `profile: ambient`. The chart has no sidecar variant to distinguish from; it is ambient-only by nature.

## The Official Production Install Order

The install sequence is dictated by dependency:

1. **Base CRDs** via the `istio/base` chart. This ships the Kubernetes CRDs (VirtualService, DestinationRule, PeerAuthentication, AuthorizationPolicy, etc.) and the cluster roles that `istiod` will bind to. No workloads. Must be installed first because everything else references these CRDs.
2. **Gateway API CRDs** installed from the upstream `kubernetes-sigs/gateway-api` release (not from Istio). Also pure CRDs. Can install in parallel with base since no ordering dependency exists between the two, but must be present before any Gateway or HTTPRoute is applied.
3. **`istiod`** via the `istio/istiod` chart with `profile: ambient`. The control plane pod. Must be Running before the data plane starts, because both `istio-cni` and `ztunnel` fail their readiness probes if they cannot fetch initial config from `istiod`.
4. **`istio-cni`** via the `istio/cni` chart with `profile: ambient`. The DaemonSet that installs the CNI plugin. Once it is Running on every node, new pods will be checked for ambient enrollment.
5. **`ztunnel`** via the `istio/ztunnel` chart. The DaemonSet that terminates HBONE. Once it is Running, ambient-enrolled pods can send traffic. If installed before `istio-cni`, ambient pods on a node will find no redirect rules and their traffic will bypass the mesh; the mesh silently under-performs rather than failing loudly.

Steps 4 and 5 can be installed back-to-back. `ztunnel` doesn't reject clients before `istio-cni` is ready, it just has nothing to talk to yet.

Steps 6 and beyond are optional per feature: a waypoint proxy for a specific tenant (`istio/gateway` chart with `gatewayClassName: istio-waypoint`), an ingress `Gateway` for external traffic (via a Gateway API `Gateway` resource, see [How Gateway API Routing Works](gateway-api.md)), an egress `Gateway` for external service calls, and so on.

## Minikube Adjustments

The `global.platform=minikube` values override on `istiod`, `istio-cni`, and `ztunnel` exists because minikube's docker driver uses non-standard host paths for CNI:

- Standard Kubernetes uses `/opt/cni/bin` for plugin binaries and `/etc/cni/net.d` for config.
- Minikube's docker driver bind-mounts these paths from inside the minikube VM, which changes what `istio-cni`'s init container sees.

With `global.platform=minikube`, the charts adjust the DaemonSet's `hostPath` volume mounts and the CNI config template's `bindir` and `confdir` fields to point at the paths minikube actually uses. Without it, `istio-cni-node` reports `Running` but its CNI plugin is never picked up by kubelet, so pods start with no ambient redirect rules. This is the same silent under-performance mode as installing `ztunnel` before `istio-cni`.

Colima with minikube behaves the same way for this purpose; the flag name reflects the minikube layer, not colima.

## References

- [Istio Ambient Mode Overview](https://istio.io/latest/docs/ambient/overview/), the architectural rationale for the L4/L7 split.
- [Istio Ambient Architecture](https://istio.io/latest/docs/ambient/architecture/), a deep dive on `ztunnel`, waypoints, and HBONE.
- [HBONE protocol design doc](https://docs.google.com/document/d/1FvfPfgUcXLXAOJTvHmyaN0zWSAt6C4S_qZO2WFQ7Rq0/), the Google Doc where the Istio team specified HBONE.
- [Ambient Mode Install (Helm)](https://istio.io/latest/docs/ambient/install/helm/), the reference install order.
- [Ambient Platform Prerequisites](https://istio.io/latest/docs/ambient/install/platform-prerequisites/), why platform flags exist and what they toggle.
- [Zero Trust Networking (BeyondCorp)](https://research.google/pubs/pub43231/), Google's original zero-trust paper and the model ambient inherits.
