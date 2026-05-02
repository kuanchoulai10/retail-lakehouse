# Trino

Deploys Trino, a distributed SQL query engine, via Helm into the `trino` namespace. Trino federates queries across the Iceberg lakehouse on S3. TLS certificates are managed by cert-manager and secrets are encrypted with SOPS/AGE.

## Deployed Resources

```
Namespace: trino
├── trino-coordinator                    (Deployment)
├── trino-worker                         (Deployment)
├── trino-selfsigned-issuer              (Issuer, cert-manager — bootstrap)
├── trino-ca                             (Certificate, cert-manager — CA, isCA=true)
├── trino-ca-issuer                      (Issuer, cert-manager — signs server + clients)
├── trino-tls                            (Certificate, cert-manager — coordinator HTTPS)
└── trino-client-<user>                  (Certificate, cert-manager — laptop / service mTLS)
```

## Namespaces

- `trino`

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
kubectl port-forward -n trino svc/trino 8443:8443 --context retail-lakehouse

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
kubectl rollout restart deployment/trino-coordinator -n trino --context retail-lakehouse
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `trino` | 8080 | HTTP (internal) |
| `trino` | 8443 | HTTPS (coordinator) — mTLS or OAuth2 |

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
