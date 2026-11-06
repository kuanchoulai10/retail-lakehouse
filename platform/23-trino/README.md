# Trino

Deploys Trino, a distributed SQL query engine, via Helm into the `lakehouse-query-engine` namespace. Trino federates queries across the Iceberg lakehouse on S3. TLS certificates are managed by cert-manager. The CLI authenticates with mTLS and the web UI logs in through Keycloak (wave `13-identity`).

## Deployed Resources

```
Namespace: lakehouse-query-engine
├── trino-coordinator                    (Deployment)
├── trino-worker                         (Deployment)
├── trino-selfsigned-issuer              (Issuer, cert-manager — bootstrap)
├── trino-ca                             (Certificate, cert-manager — CA, isCA=true)
├── trino-ca-issuer                      (Issuer, cert-manager — signs server + clients)
├── trino-tls                            (Certificate, cert-manager — coordinator HTTPS)
└── trino-client-<user>                  (Certificate, cert-manager — laptop / service mTLS)
```

## Namespaces

- `lakehouse-query-engine`

## Pods

| Pod | Purpose |
|-----|---------|
| `trino-coordinator` | Parses queries, builds execution plans, and coordinates workers |
| `trino-worker` | Executes query fragments and reads data from sources |

## Secrets

No secret is committed. `bootstrap.sh` creates them before `helm upgrade`, and Trino reads each one from an environment variable (`${ENV:…}` in the rendered properties), so the `trino-coordinator`, `trino-worker` and `trino-catalog` ConfigMaps hold only references. `validate.sh` fails if a secret property in them is not an `${ENV:}` reference, or if the coordinator still points at Google.

| Secret | Keys | Source | Env vars |
|--------|------|--------|----------|
| `trino-internal-shared-secret` | `shared-secret` | generated once (`openssl rand -hex 32`), never rotated by a rerun | `TRINO_SHARED_SECRET` |
| `trino-credentials` | `polaris-credential` | `lakehouse-catalog/polaris-bootstrap-secret` `credentials`, as `clientId:clientSecret` | `TRINO_POLARIS_CREDENTIAL` |
| | `exchange-s3-access-key`, `exchange-s3-secret-key` | `object-storage/rustfs-secret` `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY` | `TRINO_EXCHANGE_S3_ACCESS_KEY`, `TRINO_EXCHANGE_S3_SECRET_KEY` |
| | `oauth2-client-secret` | `identity/keycloak-clients` `trino-client-secret` | `TRINO_OAUTH2_CLIENT_SECRET` |

`trino-credentials` is rebuilt from its sources on every bootstrap. Two more inputs come from existing objects: `TRINO_KEYSTORE_PASSWORD` from `trino-keystore-password` (`secrets.yaml`), and `PUBLIC_ORIGIN` from the ConfigMap `trino-public-origin` (key `origin`), which `bootstrap.sh` writes from `origin::public` (`scripts/utils/origin.sh`) on every run.

Coordinator and worker pods carry the annotation `checksum/trino-env`, a hash of these Secrets and the origin ConfigMap computed by Helm `lookup` at upgrade time, so a changed credential or origin rolls the pods on the next bootstrap. `helm template` without `--dry-run=server` renders the hash of empty lookups.

## TLS Certificates

cert-manager manages a two-tier PKI for Trino, defined in `trino-certificate.yaml`:

1. `trino-selfsigned-issuer` (selfSigned) bootstraps `trino-ca` — a CA cert with `isCA: true`, stored in `trino-ca-secret`.
2. `trino-ca-issuer` (ca:) references that secret and signs the server cert (`trino-tls`) plus every client cert (`trino-client-<user>`).

Server and client certs sharing the same CA chain is what makes mTLS validation work in both directions. The coordinator init container also runs `keytool` against the same CA cert to build a PKCS12 truststore at `/etc/trino/truststore/truststore.p12`.

## Authentication

Trino is configured with `authenticationType: "certificate,oauth2"`. The coordinator tries client certificate first, then falls back to OAuth2 if no cert is presented.

- **mTLS** for `trino` CLI from a laptop and any future in-cluster service — see [Client Certificates](#client-certificates) below.
- **OAuth2 (Keycloak)** for the browser web UI: client `trino` in realm `retail-lakehouse`. The browser goes to the public issuer `${PUBLIC_ORIGIN}/keycloak/realms/retail-lakehouse`; the coordinator fetches tokens and keys from the in-cluster realm (`http://keycloak.identity.svc.cluster.local:8080/keycloak/realms/retail-lakehouse`), with OIDC discovery off. The principal is `preferred_username`. `http-server.process-forwarded=true` lets a gateway route on the HTTP port 8080 present the request as HTTPS.

The Google OAuth client that the web UI used before is no longer referenced; the owner deletes it in Google Cloud Console.

## Client Certificates

Issue a client cert for a user (or a service account name):

```bash
task trino-client-cert USER=alice KUBE_CONTEXT=retail-lakehouse
```

This applies a `Certificate` CR signed by `trino-ca-issuer` and exports:

- `23-trino/client-certs/alice/keystore.p12` — client identity (CN=alice)
- `23-trino/client-certs/alice/truststore.p12` — CA cert to trust the Trino server
- `23-trino/client-certs/alice/password.txt` — keystore password (= `trinopassword`)
- `23-trino/client-certs/alice/ca.crt` — CA cert in PEM (informational)

Cert is valid 365 days; cert-manager auto-renews 30 days before expiry. Re-run the task to refresh local files after renewal. The output directory is gitignored.

### Querying with mTLS

```bash
# 1. Port-forward (separate terminal, leave running)
kubectl port-forward -n lakehouse-query-engine svc/trino 8443:8443 --context retail-lakehouse

# 2. Query
trino \
  --server https://localhost:8443 \
  --user alice \
  --keystore-path 23-trino/client-certs/alice/keystore.p12 \
  --keystore-password "$(cat 23-trino/client-certs/alice/password.txt)" \
  --truststore-path 23-trino/client-certs/alice/truststore.p12 \
  --truststore-password "$(cat 23-trino/client-certs/alice/password.txt)" \
  --execute "SHOW CATALOGS"
```

The Trino user is derived from the cert's CN (the `USER=` value), via `http-server.authentication.certificate.user-mapping.pattern=CN=([^,]+).*`.

### End-to-End Smoke Test

```bash
task trino:smoke-test KUBE_CONTEXT=retail-lakehouse
```

Issues a throwaway cert, runs `SHOW CATALOGS`, then cleans up Certificate CR + secret + local files + port-forward.

### Browser SSO Manual Verification

After deploy, port-forward `service/trino` 8443 and open `https://localhost:8443/ui` in a browser on the tailnet. Expected: redirect to the Keycloak login at the public origin (no prompt if the browser already holds a Keycloak session), then the Trino web UI. Keycloak's `trino` client allows `https://localhost:8443/oauth2/callback` for this.

### Server Cert Rotation

cert-manager auto-renews `trino-tls`, but the truststore-building init container does not rerun on renewal (the `tls-built` emptyDir is recreated only on pod start). After a server cert rotation, manually trigger a coordinator restart:

```bash
kubectl rollout restart deployment/trino-coordinator -n lakehouse-query-engine --context retail-lakehouse
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `trino` | 8080 | HTTP (internal) |
| `trino` | 8443 | HTTPS (coordinator) — mTLS or OAuth2 |

## Memory Sizing

Trino shares the single minikube node with Kafka, Polaris, Temporal and the Spark maintenance jobs, so it is sized small. The coordinator heap is about 70% of its container memory limit. The rest is left for metaspace, code cache, thread stacks and direct buffers.

| Container | `-Xmx` | Memory request / limit | `query.max-memory-per-node` | `memory.heap-headroom-per-node` |
|-----------|--------|------------------------|-----------------------------|---------------------------------|
| `trino-coordinator` | 2G | 2816Mi / 2816Mi | 1GB | 600MB |
| `trino-worker` (each) | 3G | 4Gi / 5Gi | 1536MB | 900MB |
| `jmx-exporter` sidecar (each pod) | - | 384Mi / 384Mi | - | - |

`query.max-memory` (cluster-wide) is `3GB`, which equals two workers at 1536MB each. The coordinator does not run tasks (`node-scheduler.include-coordinator=false`). With one worker, Trino has a hard ceiling of about 8.5 GiB, and each extra worker adds about 5.4 GiB.

The worker limit was `4Gi` (request = limit) until 2026-11-03. With a 3G heap that left about 1 GiB for non-heap memory (metaspace, threads, JIT and code cache, and the direct buffers of the Iceberg / Parquet writers and the S3 client), and the container was OOMKilled at the limit twice during the table maintenance `e2e.sh` INSERT burst on 2026-11-01. It was a container OOMKill, not a Java heap OOM. The limit is now `5Gi` with the request kept at `4Gi`, so scheduling headroom for the Spark maintenance jobs is unchanged; the heap and query memory settings are unchanged.

Measured on 2026-11-03 after a clean onboard, sampling the worker's cgroup `memory.current` every 10 s: the worker peaked at 4155 MiB in the first `e2e.sh` run and 4331 MiB in the second (both above the old 4096 MiB limit, 85% of the new limit), with no OOMKill or restart; KEDA kept one worker. During the following 30 minute soak it fell from 4266 to 2567 MiB. The coordinator peaked at 1907 MiB.

## Worker Autoscaling (KEDA)

The `trino-worker` Deployment is scaled by the KEDA ScaledObject `trino-worker`, which manages the HPA `keda-hpa-trino-worker`:

- Trigger: Prometheus `prometheus-k8s.monitoring:9090`, query `sum(trino_execution_QueryManager_RunningQueries{namespace="lakehouse-query-engine",job="trino"})`. This is the coordinator's JMX metric, scraped through the `jmx-exporter` sidecar by the chart's ServiceMonitor. `prometheus-rolebinding.yaml` grants Prometheus the RBAC to discover these targets. `sum()` keeps the query to a single series during a coordinator rollout.
- Target: an average of 2 running queries per worker, with 1 to 2 workers. A third concurrent query adds the second worker.
- Scale-down: one pod per minute, after a 5-minute stabilization window.
- Fallback: after 3 failed Prometheus polls, KEDA pins the workers to 1.

Check the scaler with `kubectl get hpa keda-hpa-trino-worker -n lakehouse-query-engine --context retail-lakehouse`. `TARGETS` should show a number such as `0/2 (avg)`.

If `TARGETS` shows `<unknown>`, the HPA cannot read the external metric. The usual cause is that `keda-operator-metrics-apiserver` or `prometheus-k8s-0` is restarting, for example under node memory pressure. While the metric is unknown, the HPA keeps the current replica count and never scales down. The fallback does not help in that case, because it only acts when the KEDA operator itself sees the Prometheus query fail.

## Installation

```bash
bash 23-trino/install.sh
```

## Uninstallation

```bash
bash 23-trino/uninstall.sh
```

## Validation

```bash
bash 23-trino/validate.sh
```
