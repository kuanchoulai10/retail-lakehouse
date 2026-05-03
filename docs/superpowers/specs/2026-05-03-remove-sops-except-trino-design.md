# Remove SOPS from Project Except Trino

## Background

The project currently uses [SOPS](https://github.com/getsops/sops) with AGE encryption to protect 7 secret YAML files across the `platform/` tree. Of these, only `platform/23-trino/values-secret.yaml` contains real, sensitive credentials (Google OAuth2 client-id and client-secret used for Trino's browser SSO). The other 6 files contain dev-only credentials (MinIO root password, MySQL password, Polaris bootstrap secrets, Debezium connector credentials, Iceberg connector credentials) that are not sensitive in this dev-only project.

Maintaining SOPS for the dev-only secrets adds friction without security value: every contributor must install `sops` + `age`, manage an AGE keyfile, and decrypt before edits. The goal is to remove SOPS for those 6 files while preserving it for the one file that actually needs it.

## Goals

- Remove SOPS encryption from 6 dev-only secret files; commit them as plaintext.
- Remove SOPS calls from the 5 bootstrap scripts that decrypt those files.
- Keep SOPS protecting `platform/23-trino/values-secret.yaml` (Trino OAuth2 + internal shared secret).
- Keep `sops`/`age` listed as Taskfile preconditions (Trino still needs them).

## Non-Goals

- Rewrite git history to scrub previously-encrypted ciphertext. The historical commits stay as-is — content was ciphertext at commit time, decrypting locally and committing plaintext does not retroactively change history.
- Rotate any credentials. The 6 dev-only secrets keep their existing values; if a contributor wants fresh values, they edit the now-plaintext files.
- Change the AGE key file location or recipient public key.
- Add new secret-management tooling (e.g., External Secrets Operator, Vault).

## Files Affected

### 1. Decrypted in place (6 files)

These are decrypted with `sops -d --in-place` and committed as plaintext.

- `platform/20-minio/minio-secret.yaml`
- `platform/20-mysql/mysql-secret.yaml`
- `platform/21-polaris/polaris-storage-secret.yaml`
- `platform/21-polaris/polaris-bootstrap-secret.yaml`
- `platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml`
- `platform/22-kafka-iceberg-connector/iceberg-secret.yaml`

### 2. Bootstrap scripts updated (5 scripts)

Each `sops --decrypt … | kubectl apply -f -` line is replaced with `kubectl apply -f <file>`.

- `platform/20-minio/bootstrap.sh` (1 sops call)
- `platform/20-mysql/bootstrap.sh` (1 sops call)
- `platform/21-polaris/bootstrap.sh` (2 sops calls — storage + bootstrap)
- `platform/21-kafka-debezium-mysql-connector/bootstrap.sh` (1 sops call)
- `platform/22-kafka-iceberg-connector/bootstrap.sh` (1 sops call)

Example diff (`20-minio/bootstrap.sh`):

```diff
-sops --decrypt "$SCRIPT_DIR/minio-secret.yaml" \
-  | kubectl apply -f - --context "${KUBE_CONTEXT}"
+kubectl apply -f "$SCRIPT_DIR/minio-secret.yaml" --context "${KUBE_CONTEXT}"
```

### 3. `.sops.yaml` regex narrowed

Current rule matches every `*-secret.yaml`:

```yaml
creation_rules:
  - path_regex: .*-secret\.yaml$
    age: "age1t7azpszznty3rr4a2h6sheq0zp946ds7830a5lg9uwqrkls8rqfs4t9vjm"
```

After: only matches Trino's file, so future `*-secret.yaml` files don't get auto-encrypted by mistake:

```yaml
creation_rules:
  - path_regex: ^platform/23-trino/values-secret\.yaml$
    age: "age1t7azpszznty3rr4a2h6sheq0zp946ds7830a5lg9uwqrkls8rqfs4t9vjm"
```

### 4. Trino README minor edit

`platform/23-trino/README.md` mentions SOPS in a way that's still accurate but should clarify Trino is now the only SOPS-managed component in the project. One short clarifying sentence in the "Secrets Management" section.

### 5. Unchanged

- `platform/23-trino/values-secret.yaml` — stays encrypted.
- `platform/23-trino/bootstrap.sh` — `sops -d` to tmpfile + `helm --values` flow stays as-is.
- `taskfile.yml` and `tasks/apps.yml` — `command -v sops` precondition stays (Trino still uses it).
- AGE key location (`~/.config/sops/age/keys.txt`) — unchanged.
- Historical specs/plans referencing SOPS (e.g., `2026-04-29-polaris-db-design.md`, `2026-05-02-trino-mtls-auth-design.md`) — historical artifacts, not edited.

## Verification

After the change:

1. Each of the 6 plaintext secret files renders as a normal `kind: Secret` YAML — `kubectl apply --dry-run=client -f <file>` succeeds.
2. Each touched bootstrap script can be re-run end-to-end against the dev cluster (`KUBE_CONTEXT=retail-lakehouse bash platform/20-minio/bootstrap.sh`, etc.) and the corresponding Secret object is created/updated.
3. `task apps:validate KUBE_CONTEXT=retail-lakehouse` still passes (no regression in the platform stack).
4. Trino's bootstrap and validate scripts continue to work unchanged — SOPS still decrypts `values-secret.yaml`.

## Risks

- **Plaintext credentials in git going forward.** Acceptable per user decision: these credentials are dev-only and carry no production risk. The Trino OAuth2 secret — the only real credential — remains encrypted.
- **`.sops.yaml` regex change could surprise future contributors** who add a `*-secret.yaml` file expecting auto-encryption. Mitigated by the README clarification noting Trino is the only SOPS-managed file.
