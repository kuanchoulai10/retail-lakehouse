# Trino

Deploys Trino, a distributed SQL query engine, via Helm into the `lakehouse-query-engine` namespace. Trino federates queries across the Iceberg lakehouse on S3. TLS certificates are managed by cert-manager and secrets are encrypted with SOPS/AGE.

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

## Prerequisites

The following tools must be installed before running the installation scripts:

- [SOPS](https://github.com/getsops/sops): `brew install sops`
- [AGE](https://github.com/FiloSottile/age): `brew install age`
- [helm-secrets](https://github.com/jkroepke/helm-secrets): `helm plugin install https://github.com/jkroepke/helm-secrets`

## First-time Setup

Generate an AGE key pair (one-time per machine):

```bash
age-keygen -o ~/.config/sops/age/keys.txt
```

Copy the public key (starts with `age1...`) into `.sops.yaml` at the project root:

```yaml
creation_rules:
  - path_regex: .*/values-secret\.yaml$
    age: "age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Secrets Management

Secrets are stored in `values-secret.yaml`, encrypted with SOPS/AGE and committed to git. The file contains OAuth2 credentials, AWS keys for Iceberg/S3, and the Trino internal shared secret.

> **Note:** This is the only SOPS-managed file in the project. Other dev-only secrets under `platform/` are committed as plaintext. See `docs/superpowers/specs/2026-05-03-remove-sops-except-trino-design.md` for the rationale.

To edit secrets:

```bash
sops 23-trino/values-secret.yaml
```

SOPS decrypts the file into your editor and re-encrypts on save. The AGE private key at `~/.config/sops/age/keys.txt` is used automatically.

To encrypt a new plaintext `values-secret.yaml`:

```bash
sops --encrypt --in-place 23-trino/values-secret.yaml
```

## TLS Certificates

cert-manager manages a two-tier PKI for Trino, defined in `trino-certificate.yaml`:

1. `trino-selfsigned-issuer` (selfSigned) bootstraps `trino-ca` — a CA cert with `isCA: true`, stored in `trino-ca-secret`.
2. `trino-ca-issuer` (ca:) references that secret and signs the server cert (`trino-tls`) plus every client cert (`trino-client-<user>`).

Server and client certs sharing the same CA chain is what makes mTLS validation work in both directions. The coordinator init container also runs `keytool` against the same CA cert to build a PKCS12 truststore at `/etc/trino/truststore/truststore.p12`.

## Authentication

Trino is configured with `authenticationType: "certificate,oauth2"`. The coordinator tries client certificate first, then falls back to OAuth2 if no cert is presented.

- **mTLS** for `trino` CLI from a laptop and any future in-cluster service — see [Client Certificates](#client-certificates) below.
- **OAuth2 (Google SSO)** for the browser Web UI — config lives in SOPS-encrypted `values-secret.yaml`.

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
task trino-smoke-test KUBE_CONTEXT=retail-lakehouse
```

Issues a throwaway cert, runs `SHOW CATALOGS`, then cleans up Certificate CR + secret + local files + port-forward.

### Browser SSO Manual Verification

After deploy, open `https://localhost:8443/ui` in a browser. Expected: redirect to Google SSO, login, see the Trino Web UI.

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

Trino shares the single minikube node with Kafka, Polaris, Temporal and the Spark maintenance jobs, so it is sized small. Each JVM heap is about 75% of its container memory limit. The rest is left for metaspace, code cache, thread stacks and direct buffers, which measure about 1 GiB per Trino JVM.

| Container | `-Xmx` | Memory request = limit | `query.max-memory-per-node` | `memory.heap-headroom-per-node` |
|-----------|--------|------------------------|-----------------------------|---------------------------------|
| `trino-coordinator` | 2G | 2816Mi | 1GB | 600MB |
| `trino-worker` (each) | 3G | 4Gi | 1536MB | 900MB |
| `jmx-exporter` sidecar (each pod) | - | 384Mi | - | - |

`query.max-memory` (cluster-wide) is `3GB`, which equals two workers at 1536MB each. The coordinator does not run tasks (`node-scheduler.include-coordinator=false`). With one worker, Trino has a hard ceiling of about 7.5 GiB, and each extra worker adds about 4.4 GiB.

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
