# Remove SOPS from Project Except Trino — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decrypt 6 dev-only SOPS-encrypted secret YAML files to plaintext, drop the `sops --decrypt | kubectl apply` calls from their bootstrap scripts, and narrow `.sops.yaml` so only `platform/23-trino/values-secret.yaml` remains SOPS-managed.

**Architecture:** Mechanical infra refactor. No application code touched. Each affected unit is a self-contained pair: a `*-secret.yaml` (k8s Secret manifest) and the `bootstrap.sh` that applies it. Trino's bootstrap is the only one that keeps `sops -d` (writing to a tmpfile that helm consumes via `--values`).

**Tech Stack:** SOPS + AGE (kept only for Trino), kubectl, bash, Taskfile.

**Spec:** `docs/superpowers/specs/2026-05-03-remove-sops-except-trino-design.md`

---

### Pre-flight

- [ ] **Step 0: Confirm prerequisites**

Before starting:

1. AGE key is present:

```bash
test -f ~/.config/sops/age/keys.txt && echo OK
```

Expected: `OK`

2. `sops` binary is on PATH:

```bash
command -v sops
```

Expected: prints a path.

3. Working tree is clean:

```bash
cd /Users/kcl/Projects/retail-lakehouse && git status --short
```

Expected: empty output (no unstaged or staged changes).

---

### Task 1: Decrypt the 6 dev-only secret files

**Files:**
- Modify: `platform/20-minio/minio-secret.yaml`
- Modify: `platform/20-mysql/mysql-secret.yaml`
- Modify: `platform/21-polaris/polaris-storage-secret.yaml`
- Modify: `platform/21-polaris/polaris-bootstrap-secret.yaml`
- Modify: `platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml`
- Modify: `platform/22-kafka-iceberg-connector/iceberg-secret.yaml`

- [ ] **Step 1: Decrypt all 6 files in place**

Run from repo root (`/Users/kcl/Projects/retail-lakehouse`):

```bash
sops -d --in-place platform/20-minio/minio-secret.yaml
sops -d --in-place platform/20-mysql/mysql-secret.yaml
sops -d --in-place platform/21-polaris/polaris-storage-secret.yaml
sops -d --in-place platform/21-polaris/polaris-bootstrap-secret.yaml
sops -d --in-place platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml
sops -d --in-place platform/22-kafka-iceberg-connector/iceberg-secret.yaml
```

Expected: each command exits 0, no output. The files now begin with `apiVersion: v1` and `kind: Secret` on plain (unquoted) lines instead of `ENC[…]` blobs.

- [ ] **Step 2: Verify each file is a valid k8s Secret manifest**

For each file, run `kubectl apply --dry-run=client -f <file>` (no cluster context needed for client-side dry-run):

```bash
for f in \
  platform/20-minio/minio-secret.yaml \
  platform/20-mysql/mysql-secret.yaml \
  platform/21-polaris/polaris-storage-secret.yaml \
  platform/21-polaris/polaris-bootstrap-secret.yaml \
  platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml \
  platform/22-kafka-iceberg-connector/iceberg-secret.yaml; do
    echo "== $f =="
    kubectl apply --dry-run=client -f "$f"
done
```

Expected: each prints `secret/<name> created (dry run)`. Any error means the file did not decrypt cleanly.

- [ ] **Step 3: Verify SOPS metadata is gone**

```bash
grep -l '^sops:' platform/20-minio/minio-secret.yaml platform/20-mysql/mysql-secret.yaml platform/21-polaris/polaris-storage-secret.yaml platform/21-polaris/polaris-bootstrap-secret.yaml platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml platform/22-kafka-iceberg-connector/iceberg-secret.yaml || echo "no matches"
```

Expected: `no matches` — none of the 6 files retain the `sops:` footer block.

- [ ] **Step 4: Commit**

```bash
git add platform/20-minio/minio-secret.yaml \
        platform/20-mysql/mysql-secret.yaml \
        platform/21-polaris/polaris-storage-secret.yaml \
        platform/21-polaris/polaris-bootstrap-secret.yaml \
        platform/21-kafka-debezium-mysql-connector/debezium-secret.yaml \
        platform/22-kafka-iceberg-connector/iceberg-secret.yaml

git commit -m "$(cat <<'EOF'
refactor(platform): decrypt dev-only secret files to plaintext

Drop SOPS encryption from 6 dev-only secret manifests. These contain
non-sensitive credentials (MinIO root, MySQL, Polaris bootstrap,
Debezium connector, Iceberg connector) used only by the local dev
cluster. Trino's values-secret.yaml remains encrypted as it carries
real Google OAuth2 credentials.
EOF
)"
```

Expected: commit succeeds; pre-commit hooks (including `Detect hardcoded secrets`) pass. If the secret-detection hook flags any of these dev-only credentials, that is expected — but verify the flagged values are indeed the dev-only ones and not something pulled in by mistake.

---

### Task 2: Remove `sops --decrypt` from 5 bootstrap scripts

Each script currently pipes `sops --decrypt` into `kubectl apply -f -`. After this task, each applies the now-plaintext file directly with `kubectl apply -f <file>`.

#### 2a. `platform/20-minio/bootstrap.sh`

**Files:**
- Modify: `platform/20-minio/bootstrap.sh:12-13`

- [ ] **Step 1: Replace the sops pipe**

Change:

```bash
sops --decrypt "$SCRIPT_DIR/minio-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"
```

to:

```bash
kubectl apply -f "$SCRIPT_DIR/minio-secret.yaml" --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Lint shell**

```bash
shellcheck platform/20-minio/bootstrap.sh
```

Expected: no errors.

#### 2b. `platform/20-mysql/bootstrap.sh`

**Files:**
- Modify: `platform/20-mysql/bootstrap.sh:13`

- [ ] **Step 1: Replace the sops pipe**

Change:

```bash
sops --decrypt "$SCRIPT_DIR/mysql-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"
```

to:

```bash
kubectl apply -f "$SCRIPT_DIR/mysql-secret.yaml" --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Lint shell**

```bash
shellcheck platform/20-mysql/bootstrap.sh
```

Expected: no errors.

#### 2c. `platform/21-polaris/bootstrap.sh` (two sops calls)

**Files:**
- Modify: `platform/21-polaris/bootstrap.sh:16-19`

- [ ] **Step 1: Replace both sops pipes**

Find the two adjacent blocks:

```bash
sops --decrypt "$SCRIPT_DIR/polaris-storage-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

sops --decrypt "$SCRIPT_DIR/polaris-bootstrap-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"
```

Replace with:

```bash
kubectl apply -f "$SCRIPT_DIR/polaris-storage-secret.yaml" --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/polaris-bootstrap-secret.yaml" --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Lint shell**

```bash
shellcheck platform/21-polaris/bootstrap.sh
```

Expected: no errors.

#### 2d. `platform/21-kafka-debezium-mysql-connector/bootstrap.sh`

**Files:**
- Modify: `platform/21-kafka-debezium-mysql-connector/bootstrap.sh:10`

- [ ] **Step 1: Replace the sops pipe**

Change:

```bash
sops --decrypt "$SCRIPT_DIR/debezium-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"
```

to:

```bash
kubectl apply -f "$SCRIPT_DIR/debezium-secret.yaml" --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Lint shell**

```bash
shellcheck platform/21-kafka-debezium-mysql-connector/bootstrap.sh
```

Expected: no errors.

#### 2e. `platform/22-kafka-iceberg-connector/bootstrap.sh`

**Files:**
- Modify: `platform/22-kafka-iceberg-connector/bootstrap.sh:10`

- [ ] **Step 1: Replace the sops pipe**

Change:

```bash
sops --decrypt "$SCRIPT_DIR/iceberg-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"
```

to:

```bash
kubectl apply -f "$SCRIPT_DIR/iceberg-secret.yaml" --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Lint shell**

```bash
shellcheck platform/22-kafka-iceberg-connector/bootstrap.sh
```

Expected: no errors.

#### 2f. Sanity check + commit

- [ ] **Step 1: Confirm no remaining `sops` references in the 5 scripts**

```bash
grep -n sops \
  platform/20-minio/bootstrap.sh \
  platform/20-mysql/bootstrap.sh \
  platform/21-polaris/bootstrap.sh \
  platform/21-kafka-debezium-mysql-connector/bootstrap.sh \
  platform/22-kafka-iceberg-connector/bootstrap.sh \
  || echo "no matches"
```

Expected: `no matches`.

- [ ] **Step 2: Confirm Trino's bootstrap still uses sops (untouched)**

```bash
grep -n sops platform/23-trino/bootstrap.sh
```

Expected: prints the existing `sops -d "$SCRIPT_DIR/values-secret.yaml" > "$SECRETS_TMP"` line.

- [ ] **Step 3: Commit**

```bash
git add platform/20-minio/bootstrap.sh \
        platform/20-mysql/bootstrap.sh \
        platform/21-polaris/bootstrap.sh \
        platform/21-kafka-debezium-mysql-connector/bootstrap.sh \
        platform/22-kafka-iceberg-connector/bootstrap.sh

git commit -m "$(cat <<'EOF'
refactor(platform): drop sops decrypt pipe from 5 bootstrap scripts

The 6 dev-only secret manifests are now plaintext, so the bootstrap
scripts that apply them no longer need to pipe through sops --decrypt.
Trino's bootstrap script is unchanged — it still decrypts
values-secret.yaml to a tmpfile for helm.
EOF
)"
```

Expected: commit succeeds.

---

### Task 3: Narrow `.sops.yaml` regex

**Files:**
- Modify: `.sops.yaml`

- [ ] **Step 1: Replace the path_regex**

Edit `.sops.yaml` from:

```yaml
creation_rules:
  - path_regex: .*-secret\.yaml$
    age: "age1t7azpszznty3rr4a2h6sheq0zp946ds7830a5lg9uwqrkls8rqfs4t9vjm"
```

to:

```yaml
creation_rules:
  - path_regex: ^platform/23-trino/values-secret\.yaml$
    age: "age1t7azpszznty3rr4a2h6sheq0zp946ds7830a5lg9uwqrkls8rqfs4t9vjm"
```

- [ ] **Step 2: Verify Trino's file is still decryptable**

The decrypt path uses metadata embedded in the encrypted file (not the regex), so this is a pure sanity check that we didn't break syntax:

```bash
sops -d platform/23-trino/values-secret.yaml | head -5
```

Expected: prints plaintext YAML (starts with `server:`). No SOPS errors.

- [ ] **Step 3: Verify the regex is restrictive**

Read back the file and confirm only one creation rule, scoped to the Trino path:

```bash
cat .sops.yaml
```

Expected: shows the new `^platform/23-trino/values-secret\.yaml$` regex and nothing else.

- [ ] **Step 4: Commit**

```bash
git add .sops.yaml
git commit -m "$(cat <<'EOF'
chore(sops): narrow creation_rules regex to trino values-secret only

Trino's values-secret.yaml is now the only SOPS-managed file in the
project. Tighten the regex so future *-secret.yaml files don't get
auto-encrypted by mistake.
EOF
)"
```

Expected: commit succeeds.

---

### Task 4: Update Trino README

**Files:**
- Modify: `platform/23-trino/README.md` (the "Secrets Management" section, around line 53)

- [ ] **Step 1: Add a clarifying sentence**

Find this paragraph (currently around lines 53–55):

```markdown
## Secrets Management

Secrets are stored in `values-secret.yaml`, encrypted with SOPS/AGE and committed to git. The file contains OAuth2 credentials, AWS keys for Iceberg/S3, and the Trino internal shared secret.
```

Replace with:

```markdown
## Secrets Management

Secrets are stored in `values-secret.yaml`, encrypted with SOPS/AGE and committed to git. The file contains OAuth2 credentials, AWS keys for Iceberg/S3, and the Trino internal shared secret.

> **Note:** This is the only SOPS-managed file in the project. Other dev-only secrets under `platform/` are committed as plaintext. See `docs/superpowers/specs/2026-05-03-remove-sops-except-trino-design.md` for the rationale.
```

- [ ] **Step 2: Verify the edit**

```bash
grep -A2 "only SOPS-managed file" platform/23-trino/README.md
```

Expected: prints the new note line plus context.

- [ ] **Step 3: Commit**

```bash
git add platform/23-trino/README.md
git commit -m "$(cat <<'EOF'
docs(trino): note trino is the only sops-managed component
EOF
)"
```

Expected: commit succeeds.

---

### Task 5: End-to-end validation against the dev cluster

This task does NOT produce a commit. It's the final sanity check that the platform stack still bootstraps and validates after the change.

**Pre-condition:** the `retail-lakehouse` minikube/colima cluster is running and the relevant namespaces already exist from a prior `task apps:bootstrap`.

- [ ] **Step 1: Re-run each affected bootstrap script**

Run from repo root. These should be idempotent (`kubectl apply` semantics):

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/20-minio/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/20-mysql/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/21-polaris/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/21-kafka-debezium-mysql-connector/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/22-kafka-iceberg-connector/bootstrap.sh
```

Expected: each ends with `==> Done.` and no SOPS-related output anywhere.

- [ ] **Step 2: Re-run Trino's bootstrap (untouched, sanity only)**

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/23-trino/bootstrap.sh
```

Expected: succeeds; the helm release re-applies cleanly with the SOPS-decrypted values.

- [ ] **Step 3: Run platform validate**

```bash
task apps:validate KUBE_CONTEXT=retail-lakehouse
```

Expected: all `validate-*` subtasks pass. If any fail, investigate — the failure should be unrelated to this refactor (this change does not affect Secret content, only how it's stored at rest).

- [ ] **Step 4: Final cleanliness check**

```bash
git status --short
```

Expected: empty (everything from Tasks 1–4 already committed; this task adds no new changes).

```bash
grep -rn "sops" platform/ --include="bootstrap.sh"
```

Expected: only `platform/23-trino/bootstrap.sh` shows matches.
