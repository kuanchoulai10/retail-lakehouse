# Trino mTLS Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Trino's OAuth2-only auth with `certificate,oauth2` multi-auth so trino CLI from laptop works without Google OAuth, while keeping browser SSO functional.

**Architecture:** Same `trino-selfsigned-issuer` (cert-manager) signs both server cert (existing) and per-user client certs (new). Server adds an init container that builds a PKCS12 truststore from the CA cert. A taskfile helper signs and exports laptop client certs. OAuth2 config remains untouched as the secondary auth path.

**Tech Stack:** Trino Helm chart 1.39.1, cert-manager (Issuer namespace-scoped), Taskfile, kubectl, keytool (JRE).

**Spec:** `docs/superpowers/specs/2026-05-02-trino-mtls-auth-design.md`

**Trino chart key gotchas (verified against `23-trino/values-default.yaml`):**
- `initContainers` is **top-level** with `coordinator` / `worker` subkeys, NOT under `coordinator:`
- `additionalConfigProperties` is **top-level**, NOT under `coordinator:`
- `coordinator.additionalVolumes` / `coordinator.additionalVolumeMounts` ARE under `coordinator:`

---

## File Map

**Create:**
- `23-trino/client-certificate-template.yaml` — Certificate CR template with `${USER}` placeholders
- `docs/superpowers/plans/...` — this file

**Modify:**
- `.gitignore` — add `23-trino/client-certs/`
- `23-trino/values.yaml` — auth type, top-level `initContainers.coordinator` + `additionalConfigProperties`, coordinator volumes
- `23-trino/validate.sh` — static mTLS checks + negative test
- `taskfile.yml` — add `trino-client-cert` and `trino-smoke-test`
- `23-trino/README.md` — document mTLS flow + OAuth2 SSO manual checklist

**Generated at runtime (gitignored):**
- `23-trino/client-certs/<user>/{keystore.p12,truststore.p12,ca.crt,password.txt}`

---

### Task 1: Add client-certs dir to gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add gitignore entry**

Append to `.gitignore`:

```
# Trino client cert artifacts produced by `task trino-client-cert`
23-trino/client-certs/
```

- [ ] **Step 2: Verify**

Run:
```bash
mkdir -p 23-trino/client-certs/test && touch 23-trino/client-certs/test/keystore.p12
git status --short 23-trino/client-certs/
```
Expected: empty output (gitignored).

Cleanup:
```bash
rm -rf 23-trino/client-certs/test
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(trino): gitignore client-cert artifacts"
```

---

### Task 2: Create Certificate CR template for client certs

**Files:**
- Create: `23-trino/client-certificate-template.yaml`

- [ ] **Step 1: Create the template**

Content:
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: trino-client-${USER}
  namespace: trino
spec:
  secretName: trino-client-${USER}-tls
  duration: 8760h
  renewBefore: 720h
  issuerRef:
    name: trino-selfsigned-issuer
    kind: Issuer
  commonName: ${USER}
  subject:
    organizations:
      - Trino
  usages:
    - client auth
  privateKey:
    algorithm: RSA
    size: 2048
    encoding: PKCS8
  keystores:
    pkcs12:
      create: true
      passwordSecretRef:
        name: trino-keystore-password
        key: password
```

- [ ] **Step 2: Verify envsubst works**

Run:
```bash
USER=alice envsubst < 23-trino/client-certificate-template.yaml | grep -E "(name: trino-client|commonName)"
```
Expected:
```
  name: trino-client-alice
  commonName: alice
```

- [ ] **Step 3: Commit**

```bash
git add 23-trino/client-certificate-template.yaml
git commit -m "feat(trino): add client Certificate CR template"
```

---

### Task 3: Add `trino-client-cert` taskfile target

**Files:**
- Modify: `taskfile.yml` (add new task; place after the existing `validate-trino` task to group with trino tasks)

- [ ] **Step 1: Add the task**

Insert after `validate-trino`:

```yaml
  trino-client-cert:
    desc: 'Issue a Trino mTLS client cert. Usage: task trino-client-cert USER=alice'
    vars:
      OUTDIR: '23-trino/client-certs/{{.USER}}'
      CTX: '{{.KUBE_CONTEXT | default "mini"}}'
    cmds:
      - test -n "{{.USER}}" || (echo "ERROR: USER=<name> required"; exit 1)
      - mkdir -p {{.OUTDIR}}
      - chmod 700 {{.OUTDIR}}
      - USER={{.USER}} envsubst < 23-trino/client-certificate-template.yaml | kubectl apply -f - --context {{.CTX}}
      - kubectl wait --for=condition=Ready certificate/trino-client-{{.USER}} -n trino --timeout=120s --context {{.CTX}}
      - kubectl get -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}} -o jsonpath='{.data.keystore\.p12}' | base64 -d > {{.OUTDIR}}/keystore.p12
      - kubectl get -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}} -o jsonpath='{.data.ca\.crt}' | base64 -d > {{.OUTDIR}}/ca.crt
      - kubectl get -n trino secret trino-keystore-password --context {{.CTX}} -o jsonpath='{.data.password}' | base64 -d > {{.OUTDIR}}/password.txt
      - rm -f {{.OUTDIR}}/truststore.p12
      - keytool -importcert -noprompt -alias trino-ca -file {{.OUTDIR}}/ca.crt -keystore {{.OUTDIR}}/truststore.p12 -storetype PKCS12 -storepass "$(cat {{.OUTDIR}}/password.txt)"
      - chmod 600 {{.OUTDIR}}/keystore.p12 {{.OUTDIR}}/truststore.p12 {{.OUTDIR}}/ca.crt {{.OUTDIR}}/password.txt
      - echo "✓ {{.OUTDIR}}/{keystore.p12, truststore.p12, password.txt}"
```

(Note: `rm -f truststore.p12` before `keytool` makes the target idempotent — `keytool -importcert` errors if the alias already exists.)

- [ ] **Step 2: Verify task exists**

Run:
```bash
task --list | grep trino-client-cert
```
Expected: line containing `trino-client-cert`.

- [ ] **Step 3: Smoke test the helper (will fail at this point — server not configured yet)**

Run:
```bash
task trino-client-cert USER=plan-test KUBE_CONTEXT=retail-lakehouse
```
Expected: succeeds — Certificate CR is created, secret extracted, files written. We don't need server-side mTLS to be live for the helper to issue a cert.

Verify files:
```bash
ls -la 23-trino/client-certs/plan-test/
```
Expected: `keystore.p12`, `truststore.p12`, `ca.crt`, `password.txt` all mode 600.

- [ ] **Step 4: Cleanup test cert**

```bash
kubectl delete -n trino certificate trino-client-plan-test --context retail-lakehouse
kubectl delete -n trino secret trino-client-plan-test-tls --context retail-lakehouse --ignore-not-found
rm -rf 23-trino/client-certs/plan-test
```

- [ ] **Step 5: Commit**

```bash
git add taskfile.yml
git commit -m "feat(trino): add trino-client-cert task to issue laptop mTLS certs"
```

---

### Task 4: Add init container + truststore volume in values.yaml

**Files:**
- Modify: `23-trino/values.yaml`

- [ ] **Step 1: Add top-level `initContainers.coordinator`**

Add this **at the top level** of `23-trino/values.yaml` (NOT under `coordinator:`). Place it after the `# --8<-- [end:server]` block and before `# --8<-- [start:resource-groups]`:

```yaml
# --8<-- [start:initContainers]
initContainers:
  coordinator:
    - name: build-truststore
      image: eclipse-temurin:21-jre
      command:
        - sh
        - -c
        - |
          keytool -importcert -noprompt \
            -alias trino-ca \
            -file /tls-src/ca.crt \
            -keystore /tls-built/truststore.p12 \
            -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD"
      env:
        - name: KEYSTORE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: trino-keystore-password
              key: password
      volumeMounts:
        - name: tls-certs
          mountPath: /tls-src
          readOnly: true
        - name: tls-built
          mountPath: /tls-built
# --8<-- [end:initContainers]
```

- [ ] **Step 2: Add new volume + mount under `coordinator:`**

Modify the existing `coordinator.additionalVolumes` and `coordinator.additionalVolumeMounts` to also include the `tls-built` emptyDir:

```yaml
coordinator:
  # ... existing keys unchanged ...
  additionalVolumes:
    - name: tls-certs
      secret:
        secretName: trino-tls-secret
    - name: tls-built
      emptyDir: {}
  additionalVolumeMounts:
    - name: tls-certs
      mountPath: /etc/trino/tls
      readOnly: true
    - name: tls-built
      mountPath: /etc/trino/truststore
      readOnly: true
```

- [ ] **Step 3: Redeploy**

Run:
```bash
bash 23-trino/install.sh
```
Expected: helm upgrade succeeds; coordinator pod restarts.

- [ ] **Step 4: Wait for coordinator ready**

```bash
kubectl rollout status deployment/trino-coordinator -n trino --context retail-lakehouse --timeout=180s
```
Expected: `deployment "trino-coordinator" successfully rolled out`.

- [ ] **Step 5: Verify init container ran and truststore exists**

```bash
kubectl exec -n trino deployment/trino-coordinator --context retail-lakehouse -- ls -la /etc/trino/truststore/truststore.p12
```
Expected: file exists, non-zero size.

- [ ] **Step 6: Verify init container logs are clean**

```bash
kubectl logs -n trino deployment/trino-coordinator -c build-truststore --context retail-lakehouse
```
Expected: `Certificate was added to keystore` or similar success message; no errors.

- [ ] **Step 7: Commit**

```bash
git add 23-trino/values.yaml
git commit -m "feat(trino): add init container that builds CA truststore for mTLS"
```

---

### Task 5: Switch authenticationType + add mTLS config properties

**Files:**
- Modify: `23-trino/values.yaml`

- [ ] **Step 1: Change `authenticationType`**

In `23-trino/values.yaml`, find:
```yaml
server:
  workers: 2
  config:
    authenticationType: "oauth2"
```

Change to:
```yaml
server:
  workers: 2
  config:
    authenticationType: "certificate,oauth2"
```

- [ ] **Step 2: Add top-level `additionalConfigProperties`**

Add **at the top level** of `23-trino/values.yaml` (NOT under `coordinator:`). Place after the `# --8<-- [end:initContainers]` block:

```yaml
# --8<-- [start:additionalConfigProperties]
additionalConfigProperties:
  - http-server.https.truststore.path=/etc/trino/truststore/truststore.p12
  - http-server.https.truststore.key=trinopassword
  - http-server.authentication.certificate.user-mapping.pattern=CN=([^,]+).*
# --8<-- [end:additionalConfigProperties]
```

- [ ] **Step 3: Redeploy**

```bash
bash 23-trino/install.sh
kubectl rollout status deployment/trino-coordinator -n trino --context retail-lakehouse --timeout=180s
```
Expected: rollout succeeds.

- [ ] **Step 4: Verify rendered config**

```bash
kubectl exec -n trino deployment/trino-coordinator --context retail-lakehouse -- cat /etc/trino/config.properties
```
Expected output includes:
```
http-server.authentication.type=certificate,oauth2
http-server.https.truststore.path=/etc/trino/truststore/truststore.p12
http-server.https.truststore.key=trinopassword
http-server.authentication.certificate.user-mapping.pattern=CN=([^,]+).*
```

If `config.properties` lives at a different path, find it:
```bash
kubectl exec -n trino deployment/trino-coordinator --context retail-lakehouse -- sh -c 'find /etc/trino -name config.properties'
```
Adjust the path in Task 6's checks accordingly.

- [ ] **Step 5: End-to-end test with the helper from Task 3**

```bash
task trino-client-cert USER=plan-test KUBE_CONTEXT=retail-lakehouse
kubectl port-forward -n trino svc/trino 18443:8443 --context retail-lakehouse &
PF_PID=$!
sleep 2
trino --server https://localhost:18443 --user plan-test \
  --keystore-path 23-trino/client-certs/plan-test/keystore.p12 \
  --keystore-password "$(cat 23-trino/client-certs/plan-test/password.txt)" \
  --truststore-path 23-trino/client-certs/plan-test/truststore.p12 \
  --truststore-password "$(cat 23-trino/client-certs/plan-test/password.txt)" \
  --execute "SHOW CATALOGS"
kill $PF_PID
```
Expected: query returns the catalog list (`faker`, etc.). No auth errors.

- [ ] **Step 6: Cleanup**

```bash
kubectl delete -n trino certificate trino-client-plan-test --context retail-lakehouse
kubectl delete -n trino secret trino-client-plan-test-tls --context retail-lakehouse --ignore-not-found
rm -rf 23-trino/client-certs/plan-test
```

- [ ] **Step 7: Commit**

```bash
git add 23-trino/values.yaml
git commit -m "feat(trino): enable mTLS auth alongside oauth2"
```

---

### Task 6: Add validate.sh static mTLS checks

**Files:**
- Modify: `23-trino/validate.sh`

- [ ] **Step 1: Append checks**

Append to `23-trino/validate.sh` (before the final `echo "==> Trino is ready."`):

```bash
echo "==> Validating mTLS truststore exists in coordinator"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  test -s /etc/trino/truststore/truststore.p12

echo "==> Validating authentication.type includes certificate"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.type=certificate,oauth2$' /etc/trino/config.properties

echo "==> Validating user-mapping pattern set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.certificate.user-mapping.pattern=' /etc/trino/config.properties

echo "==> Validating truststore path set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.https.truststore.path=' /etc/trino/config.properties
```

- [ ] **Step 2: Run validate.sh — should pass**

```bash
KUBE_CONTEXT=retail-lakehouse bash 23-trino/validate.sh
```
Expected: all four new checks pass; script exits 0.

- [ ] **Step 3: Commit**

```bash
git add 23-trino/validate.sh
git commit -m "test(trino): validate mTLS config in coordinator"
```

---

### Task 7: Add validate.sh negative test (unauthenticated → 401/403)

**Files:**
- Modify: `23-trino/validate.sh`

- [ ] **Step 1: Append negative test**

Append before final `echo "==> Trino is ready."`:

```bash
echo "==> Validating server rejects unauthenticated HTTPS request"
STATUS=$(kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  curl -sk -o /dev/null -w "%{http_code}" https://localhost:8443/v1/statement -X POST -d 'SELECT 1')
case "$STATUS" in
  401|403) echo "  Server rejected unauth request with HTTP $STATUS (expected)";;
  *) echo "ERROR: expected 401/403, got $STATUS"; exit 1;;
esac
```

- [ ] **Step 2: Run validate.sh — should pass**

```bash
KUBE_CONTEXT=retail-lakehouse bash 23-trino/validate.sh
```
Expected: negative test prints `Server rejected unauth request with HTTP 401` (or 403); script exits 0.

- [ ] **Step 3: Commit**

```bash
git add 23-trino/validate.sh
git commit -m "test(trino): negative auth test for HTTPS without cert"
```

---

### Task 8: Add `trino-smoke-test` taskfile target

**Files:**
- Modify: `taskfile.yml`

- [ ] **Step 1: Add the task**

Insert after `trino-client-cert`:

```yaml
  trino-smoke-test:
    desc: 'End-to-end mTLS smoke test (issues throwaway cert, runs SHOW CATALOGS, cleans up)'
    vars:
      USER: 'smoke-test'
      OUTDIR: '23-trino/client-certs/smoke-test'
      CTX: '{{.KUBE_CONTEXT | default "mini"}}'
    cmds:
      - task: trino-client-cert
        vars:
          USER: '{{.USER}}'
      - defer: kubectl delete -n trino certificate trino-client-{{.USER}} --context {{.CTX}} --ignore-not-found
      - defer: kubectl delete -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}} --ignore-not-found
      - defer: rm -rf {{.OUTDIR}}
      - defer: pkill -f 'port-forward.*trino' || true
      - kubectl port-forward -n trino svc/trino 18443:8443 --context {{.CTX}} &
      - sleep 2
      - |
        trino --server https://localhost:18443 --user {{.USER}} \
          --keystore-path {{.OUTDIR}}/keystore.p12 \
          --keystore-password "$(cat {{.OUTDIR}}/password.txt)" \
          --truststore-path {{.OUTDIR}}/truststore.p12 \
          --truststore-password "$(cat {{.OUTDIR}}/password.txt)" \
          --execute "SHOW CATALOGS"
```

(`defer` tasks run in reverse order on completion, ensuring cleanup even if the query fails.)

- [ ] **Step 2: Run smoke test**

```bash
task trino-smoke-test KUBE_CONTEXT=retail-lakehouse
```
Expected:
1. Cert is issued
2. Port-forward starts
3. `SHOW CATALOGS` returns the catalog list (e.g. `faker`)
4. Cleanup: cert/secret deleted, port-forward killed, output dir removed

- [ ] **Step 3: Verify cleanup**

```bash
kubectl get -n trino certificate trino-client-smoke-test --context retail-lakehouse 2>&1 | grep -i 'not found'
ls 23-trino/client-certs/smoke-test 2>&1 | grep -i 'no such file'
```
Expected: both confirm absence.

- [ ] **Step 4: Commit**

```bash
git add taskfile.yml
git commit -m "test(trino): add trino-smoke-test for end-to-end mTLS verification"
```

---

### Task 9: Update README with mTLS flow + OAuth2 SSO checklist

**Files:**
- Modify: `23-trino/README.md`

- [ ] **Step 1: Replace the "Services" section's HTTPS row description and add new sections**

Find:
```markdown
| `trino` | 8443 | HTTPS (coordinator, OAuth2 + KEDA metrics) |
```
Change to:
```markdown
| `trino` | 8443 | HTTPS (coordinator) — mTLS or OAuth2 |
```

After the existing `## TLS Certificates` section, add:

```markdown
## Authentication

Trino is configured with `authenticationType: "certificate,oauth2"`. The coordinator tries client certificate first, falls back to OAuth2 if no cert is presented.

- **mTLS (programmatic clients, trino CLI from laptop)** — see `## Client Certificates` below
- **OAuth2 (browser SSO)** — Google OAuth, configured in SOPS-encrypted `values-secret.yaml`

## Client Certificates

Issue a client cert for yourself (or a service account name):

\`\`\`bash
task trino-client-cert USER=alice KUBE_CONTEXT=retail-lakehouse
\`\`\`

This signs a Certificate via cert-manager (`trino-selfsigned-issuer`) and exports:
- `23-trino/client-certs/alice/keystore.p12` — your client identity
- `23-trino/client-certs/alice/truststore.p12` — CA cert to trust the Trino server
- `23-trino/client-certs/alice/password.txt` — keystore password (= `trinopassword`)

Cert is valid 365 days; cert-manager auto-renews 30 days before expiry. Re-run the task to refresh local files after renewal.

### Querying with mTLS

\`\`\`bash
# 1. Port-forward (separate terminal)
kubectl port-forward -n trino svc/trino 8443:8443 --context retail-lakehouse

# 2. Query
trino \\
  --server https://localhost:8443 \\
  --user alice \\
  --keystore-path 23-trino/client-certs/alice/keystore.p12 \\
  --keystore-password "$(cat 23-trino/client-certs/alice/password.txt)" \\
  --truststore-path 23-trino/client-certs/alice/truststore.p12 \\
  --truststore-password "$(cat 23-trino/client-certs/alice/password.txt)" \\
  --execute "SHOW CATALOGS"
\`\`\`

The Trino user is derived from the cert's CN (the value of `USER=`).

### End-to-End Smoke Test

\`\`\`bash
task trino-smoke-test KUBE_CONTEXT=retail-lakehouse
\`\`\`

Issues a throwaway cert, runs `SHOW CATALOGS`, cleans up.

### OAuth2 (Browser SSO) — Manual Verification

After deploy, open `https://localhost:8443/ui` in a browser. Expected: redirect to Google SSO, login, see Trino Web UI.

### Certificate Rotation

cert-manager auto-renews `trino-tls` (server cert), but the truststore init container does not rerun on renewal. After a server cert rotation, manually trigger a coordinator restart:

\`\`\`bash
kubectl rollout restart deployment/trino-coordinator -n trino --context retail-lakehouse
\`\`\`
```

(Note: The README uses backticks normally; in this plan they're escaped because the plan itself is a markdown code block. Use unescaped backticks in the actual README.)

- [ ] **Step 2: Verify README renders sensibly**

Run:
```bash
cat 23-trino/README.md | head -100
```
Expected: new sections present, no broken markdown.

- [ ] **Step 3: Commit**

```bash
git add 23-trino/README.md
git commit -m "docs(trino): document mTLS client cert flow and OAuth2 SSO checklist"
```

---

## Self-Review

**Spec coverage:**
- Decisions → Tasks 4, 5 (multi-auth + truststore + user-mapping)
- PKI structure → Tasks 2, 4
- CN format `CN=<username>` → Task 5 (user-mapping pattern)
- Keystore password sharing → Tasks 2, 4 (both reference `trino-keystore-password`)
- Independent init container → Task 4
- Laptop cert flow → Tasks 2, 3
- Cert duration 365 days → Task 2
- Output to project dir + gitignore → Tasks 1, 3
- In-cluster pattern (template-only, not implemented) → covered in spec, no implementation task (correct)
- validate.sh static checks → Task 6
- Negative test → Task 7
- Smoke test target → Task 8
- OAuth2 manual checklist in README → Task 9

**Placeholders:** None. Every step has actual content.

**Type/name consistency:**
- `trino-client-${USER}` Certificate name — used in template (Task 2), helper (Task 3), smoke test (Task 8) ✓
- `trino-client-${USER}-tls` secret name — same chain ✓
- `trino-keystore-password` — referenced consistently ✓
- `/etc/trino/truststore/truststore.p12` path — Task 4 mounts it, Task 5 references it, Task 6 validates it ✓
- `tls-built` volume name — defined Task 4, referenced consistently ✓

**Spec ↔ plan deltas (intentional):**
- Spec showed init container under `coordinator.initContainers` — actual chart key is top-level `initContainers.coordinator`. Plan uses correct chart key.
- Spec showed `additionalConfigProperties` under `coordinator:` — actual chart key is top-level. Plan uses correct chart key.
- These are corrections during plan writing, not behavioral changes.
