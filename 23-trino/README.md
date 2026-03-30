# Trino

Deploys Trino, a distributed SQL query engine, via Helm into the `trino` namespace. Trino federates queries across the Iceberg lakehouse on S3. TLS certificates are managed by cert-manager and secrets are encrypted with SOPS/AGE.

## Deployed Resources

```
Namespace: trino
├── trino-coordinator                    (Deployment)
├── trino-worker                         (Deployment)
├── trino-tls                            (Certificate, cert-manager)
└── trino-selfsigned-issuer              (Issuer, cert-manager)
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

cert-manager automatically provisions and renews a self-signed TLS certificate for Trino. The `trino-certificate.yaml` manifest defines a namespace-scoped `Issuer` and a `Certificate` resource that targets the `trino-tls-secret` Kubernetes Secret. The coordinator init container concatenates the separate `tls.key` and `tls.crt` files produced by cert-manager into a single PEM file at `/etc/trino/tls/trino-dev.pem`, which Trino's HTTPS keystore requires.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `trino` | 8080 | HTTP (internal) |
| `trino` | 8443 | HTTPS (coordinator, OAuth2 + KEDA metrics) |

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
