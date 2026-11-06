# Keycloak Single Sign-On Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One Keycloak login in front of every platform UI on `platform-gateway`. Trino's web UI also logs in through Keycloak, and SOPS is removed from the project.

**Architecture:** A new wave `13-identity` (namespace `identity`) runs Keycloak with its PostgreSQL and oauth2-proxy. The Istio ext_authz provider (configured in `12-istiod`) and a `CUSTOM` AuthorizationPolicy on `platform-gateway` make every path except `/keycloak`, `/sso` and `/polaris` require a session. Trino moves its settings from the SOPS file into `values.yaml` and its secrets into Kubernetes Secrets read through `${ENV:…}`. It points its OAuth2 at Keycloak and gets an HTTPRoute for `/ui` and `/oauth2` on its HTTP port 8080.

**Tech Stack:** Keycloak, oauth2-proxy, PostgreSQL, Istio ambient (ext_authz on the Gateway API gateway), Trino Helm chart 1.39.1 (Trino 476), bash wave scripts, pytest for script helpers.

**Spec:** `docs/superpowers/specs/2026-11-06-keycloak-single-sign-on-design.md`

## Global Constraints

- **CLAUDE.md applies.**
  - No `cd`.
  - `kubectl <verb>` first, flags last.
  - Every script requires `KUBE_CONTEXT` and has no fallback.
  - Commands use `KUBE_CONTEXT=retail-lakehouse`.
  - No explanatory comments in YAML.
  - Images are pinned to exact versions.
  - Commits are conventional, start lowercase and end with the session trailer.
- **Kubernetes label standard** (enforced by `scripts/check_k8s_labels.py`, the pre-commit hook `k8s-labels`).
  - Every authored object carries `app.kubernetes.io/{name,instance,part-of,managed-by}` and `component` where it applies.
  - Pod templates also carry `app.kubernetes.io/version`, equal to a container image tag.
  - Selectors use only `name` and `instance`.
- **Namespace `identity`.** Created with `namespace::apply_ambient identity` and `gateway::allow_routes identity`. Its `validate.sh` asserts `namespace::assert_ambient identity`, `gateway::assert_routes_allowed identity` and `mesh::assert_hbone identity`.
- **Generated secrets.**
  - Created only when `kubectl get` reports them missing (`--ignore-not-found -o name` is empty), with `kubectl create` and never `apply`. This is the `table-maintenance-db` pattern in `platform/25-lakehouse-control-plane/bootstrap.sh`.
  - Never printed, never committed.
  - Rerunning a bootstrap must not change them.
- **Public origin** comes only from `origin::public` (Task 1). It is never written into a committed manifest.
- **Gate.** Realm `retail-lakehouse`. Ungated path prefixes are exactly `/keycloak`, `/sso` and `/polaris`.
- **SOPS.** The builder never runs `sops`. After Task 5 nothing in the deploy path calls it.
- **Memory.** Size requests from measured usage, not equal to limits. If the measured new total would leave room for fewer than two concurrent Spark driver + executor pairs, stop and report.

## Fixed names (used across tasks)

| Thing | Value |
|---|---|
| Keycloak Service | `keycloak.identity.svc.cluster.local:8080`, HTTP relative path `/keycloak` |
| Keycloak DB Service | `keycloak-db.identity.svc.cluster.local:5432`, database and user `keycloak` |
| oauth2-proxy Service | `oauth2-proxy.identity.svc.cluster.local:4180`, proxy prefix `/sso` |
| Public issuer | `${PUBLIC_ORIGIN}/keycloak/realms/retail-lakehouse` |
| In-cluster realm base | `http://keycloak.identity.svc.cluster.local:8080/keycloak/realms/retail-lakehouse` |
| Clients | `oauth2-proxy` and `trino` (confidential, standard flow), `platform-validate` (service account only) |
| Human user | `platform-admin`, email `platform-admin@retail-lakehouse.local`, email verified |
| Secret `identity/keycloak-db` | `username`, `password`, `database` |
| Secret `identity/keycloak-admin` | `username`, `password` (Keycloak bootstrap admin) |
| Secret `identity/keycloak-clients` | `oauth2-proxy-client-secret`, `trino-client-secret`, `platform-validate-client-secret`, `platform-admin-password` |
| Secret `identity/oauth2-proxy-cookie` | `cookie-secret` (32 random bytes, URL-safe base64) |
| ConfigMap `identity/public-origin` | `origin` |
| Istio extension provider | `oauth2-proxy` |
| AuthorizationPolicy | `platform-gateway-sso` in `istio-ingress` |
| Trino secrets, in `lakehouse-query-engine` | `trino-internal-shared-secret` (`shared-secret`, generated once) and `trino-credentials` (`polaris-credential`, `exchange-s3-access-key`, `exchange-s3-secret-key`, `oauth2-client-secret`, refreshed on every bootstrap from their sources) |
| Trino env vars | `PUBLIC_ORIGIN`, `TRINO_KEYSTORE_PASSWORD`, `TRINO_SHARED_SECRET`, `TRINO_POLARIS_CREDENTIAL`, `TRINO_EXCHANGE_S3_ACCESS_KEY`, `TRINO_EXCHANGE_S3_SECRET_KEY`, `TRINO_OAUTH2_CLIENT_SECRET` |

## Review Focus

1. **Rerunning a bootstrap on a live cluster.** It must rotate no generated secret, must not lock validation out behind the gate, and must not re-import over the realm. Tasks 3 and 4 run their bootstrap twice and compare Secret `resourceVersion`s.
2. **Tailscale names.** `tailscale status --json` reports a MagicDNS name with a trailing dot, sometimes in mixed case. A wrong origin breaks every redirect. Task 1 tests the trailing dot, uppercase and missing-tailscale cases.
3. **`${ENV:…}` inside a value.** The issuer and auth URL substitute `${ENV:PUBLIC_ORIGIN}` in the middle of a value, and the substitution is also used in catalog and exchange-manager files. If Trino 476 does not substitute any of them, the coordinator or workers fail to start or log in. Task 5 checks the rendered values from inside the running coordinator.
4. **Bearer tokens that are not for the gate.** The Polaris console sends Polaris tokens to `/polaris`, which must not be rejected. Task 4 asserts that `/polaris` returns Polaris's own 401 without a session, and the browser check in Task 7 logs in to the Polaris console.
5. **Returning to the requested page.** After login the browser must land on the original path, query string included, not on `/`. Task 7 opens `/console/tables?x=1` cold and checks where it lands.

---

### Task 1: Public origin helper

**Files:**
- Create: `scripts/utils/origin.sh`
- Test: `scripts/tests/test_origin.py`

**Interfaces:**
- Produces: `origin::public`, a bash function. It prints the public origin with no trailing slash and returns 0, or prints an error to stderr and returns 1. The rule: when `PUBLIC_ORIGIN` is set and non-empty, print it with any trailing `/` removed. Otherwise read `tailscale status --json`, take `.Self.DNSName`, strip the trailing `.`, lowercase it and print `https://<name>:8591`. If `tailscale` is missing or the name is empty, fail with `public origin unknown: set PUBLIC_ORIGIN or run tailscale`.

- [ ] **Step 1: Write the failing tests.** Each test runs `bash -c 'source scripts/utils/origin.sh; origin::public'` through `subprocess`. A fake `tailscale` executable sits in a tmp dir prepended to `PATH`, and the tests use `env` to control `PUBLIC_ORIGIN`.

```python
def test_override_wins(fake_tailscale):          # PUBLIC_ORIGIN=https://x.example:8591/ -> "https://x.example:8591"
def test_detects_tailscale_name(fake_tailscale): # DNSName "Host.Tail1.ts.net." -> "https://host.tail1.ts.net:8591"
def test_fails_without_tailscale():              # PATH without tailscale, no override -> returncode 1, stderr contains "public origin unknown"
def test_fails_on_empty_dns_name(fake_tailscale):# DNSName "" -> returncode 1
```

- [ ] **Step 2: Run them and see them fail.**

  Run: `uv run --with pytest pytest scripts/tests/test_origin.py -v`

  Expected: FAIL (`origin.sh` does not exist).

- [ ] **Step 3: Implement `scripts/utils/origin.sh`.** Follow the style of `scripts/utils/gateway.sh`: a header comment listing the function, and a `__ORIGIN_SH_LOADED` guard. Use `jq` for the JSON.

- [ ] **Step 4: Run the tests again and see them pass.** Same command. Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add scripts/utils/origin.sh scripts/tests/test_origin.py
git commit -m "feat(platform): detect the public origin of the platform gateway"
```

### Task 2: Istio ext_authz provider

**Files:**
- Modify: `platform/12-istiod/values.yaml` (under `meshConfig`)
- Modify: `platform/12-istiod/validate.sh`
- Modify: `platform/12-istiod/README.md`

**Interfaces:**
- Produces: the mesh extension provider `oauth2-proxy`, of type `envoyExtAuthzHttp`, pointing at `oauth2-proxy.identity.svc.cluster.local` port `4180`.
  - Request headers sent in the check: at least `cookie`, `authorization`, `x-forwarded-proto`, `x-forwarded-host` and `x-forwarded-for`.
  - Headers sent upstream on allow: `x-auth-request-user`, `x-auth-request-email`, `x-auth-request-preferred-username`.
  - Headers sent downstream on deny: at least `location`, `set-cookie` and `content-type`, so an unauthenticated browser receives oauth2-proxy's redirect.
  - Nothing references the provider until Task 4.

- [ ] **Step 1: Write the failing check.** In `validate.sh`, read the `istio` ConfigMap in `istio-system` and fail unless its `mesh` data contains an extension provider named `oauth2-proxy`.
- [ ] **Step 2: Run it and see it fail.**

  Run: `KUBE_CONTEXT=retail-lakehouse bash platform/12-istiod/validate.sh`

  Expected: FAIL on the new check.

- [ ] **Step 3: Add the provider to `values.yaml`** with the header lists above, then run `KUBE_CONTEXT=retail-lakehouse bash platform/12-istiod/bootstrap.sh`.
- [ ] **Step 4: Run `validate.sh` again and see it pass.** Also run `KUBE_CONTEXT=retail-lakehouse bash platform/12-platform-gateway/validate.sh`. Expected: both pass. The gateway is unaffected because nothing uses the provider yet.
- [ ] **Step 5: Commit.** Add a README line on the provider.

```bash
git add platform/12-istiod/values.yaml platform/12-istiod/validate.sh platform/12-istiod/README.md
git commit -m "feat(platform): register oauth2-proxy as an istio ext_authz provider"
```

### Task 3: Wave `13-identity`, Keycloak

**Files:**
- Create in `platform/13-identity/`:
  - `bootstrap.sh`, `validate.sh`
  - `keycloak-db-pvc.yaml`, `keycloak-db-deployment.yaml`, `keycloak-db-service.yaml`
  - `keycloak-realm-configmap.yaml`, `keycloak-deployment.yaml`, `keycloak-service.yaml`, `keycloak-route.yaml`
  - `README.md`
- Modify: `tasks/apps.yml`. Add `13-identity` bootstrap and validate after `12-platform-gateway` in `cmds`, and its validate after `12-platform-gateway` in `status`.
- Modify: `scripts/utils/gateway.sh`. Add `gateway::token`.

**Interfaces:**
- Consumes: `origin::public` (Task 1).
- Produces:
  - The Services, Secrets and ConfigMap in "Fixed names".
  - The realm `retail-lakehouse` with the three clients and the user. The realm JSON uses Keycloak import placeholders (`${PUBLIC_ORIGIN}`, `${OAUTH2_PROXY_CLIENT_SECRET}`, `${TRINO_CLIENT_SECRET}`, `${PLATFORM_VALIDATE_CLIENT_SECRET}`, `${PLATFORM_ADMIN_PASSWORD}`), filled from the pod env, so no manifest holds the origin or a secret.
  - `gateway::token`, a bash function that prints a `platform-validate` access token from the in-cluster realm base. It returns 1 when `identity/keycloak-clients` does not exist.

**Realm requirements:**
- Clients:
  - `oauth2-proxy`: redirect URI `${PUBLIC_ORIGIN}/sso/callback`, plus an audience mapper adding `oauth2-proxy`.
  - `trino`: redirect URIs `${PUBLIC_ORIGIN}/oauth2/callback` and `https://localhost:8443/oauth2/callback`.
  - `platform-validate`: service account only, plus an audience mapper adding `oauth2-proxy`, so oauth2-proxy accepts its tokens.
- User `platform-admin` has first name, last name and verified email set, so Keycloak's user profile adds no required action at first login. The password is not temporary.

**Keycloak requirements:**
- Hostname `${PUBLIC_ORIGIN}/keycloak` with backchannel dynamic, HTTP enabled, relative path `/keycloak`, proxy headers `xforwarded`, health and metrics enabled.
- Start with `--import-realm`.
- Bounded heap. Readiness on the management health endpoint.
- The current stable image, pinned.

`keycloak-db` follows the `20-temporal-db` manifests with generated credentials.

- [ ] **Step 1: Write the failing checks in `validate.sh`.**
  - Ambient, routes allowed and the route Accepted.
  - Rollouts of `keycloak-db` and `keycloak`.
  - `mesh::assert_hbone identity`.
  - `gateway::curl /keycloak/realms/retail-lakehouse/.well-known/openid-configuration -fsS | jq -r .issuer` equals `$(origin::public)/keycloak/realms/retail-lakehouse`.
  - `gateway::token` prints a non-empty token whose decoded payload has `iss` equal to that issuer and `aud` containing `oauth2-proxy`.
- [ ] **Step 2: Run it and see it fail.**

  Run: `KUBE_CONTEXT=retail-lakehouse bash platform/13-identity/validate.sh`

  Expected: FAIL (the namespace is missing).

- [ ] **Step 3: Implement the manifests, `bootstrap.sh` and `gateway::token`.** `bootstrap.sh` does these in order:
  1. Namespace.
  2. Generated Secrets.
  3. ConfigMap `public-origin` from `origin::public` (applied on every run).
  4. Database, then Keycloak, then the route.
  5. Wait for the Keycloak rollout.
- [ ] **Step 4: Run the bootstrap, then `validate.sh`, and see it pass.** Then run the bootstrap a second time and confirm the `resourceVersion` of all four generated Secrets is unchanged (Review Focus 1). Record Keycloak's and keycloak-db's memory from `kubectl top pods --namespace identity` for Task 7.
- [ ] **Step 5: Commit.** The README covers the deployed resources, how to read the `platform-admin` password with `kubectl`, and that realm edits on a running cluster are manual because the import only creates a missing realm.

```bash
git add platform/13-identity tasks/apps.yml scripts/utils/gateway.sh
git commit -m "feat(platform): deploy Keycloak in wave 13-identity"
```

### Task 4: oauth2-proxy and the gateway gate

**Files:**
- Create in `platform/13-identity/`: `oauth2-proxy-deployment.yaml`, `oauth2-proxy-service.yaml`, `oauth2-proxy-route.yaml`, `platform-gateway-sso-policy.yaml`
- Modify: `platform/13-identity/bootstrap.sh`, `platform/13-identity/validate.sh`, `platform/13-identity/README.md`
- Modify: `scripts/utils/gateway.sh`

**Interfaces:**
- Consumes: the clients, the cookie Secret and `public-origin` (Task 3), and the provider `oauth2-proxy` (Task 2).
- Produces:
  - `gateway::curl` sends `Authorization: Bearer $(gateway::token)` when `gateway::token` succeeds, and sends no header when it fails. Callers do not change.
  - `gateway::curl_anonymous <path> [curl args]`: the same call, never with a token.

**oauth2-proxy requirements:**
- Provider `keycloak-oidc`.
- Issuer: the public issuer.
- OIDC discovery skipped. The login URL is public. The redeem, JWKS and profile URLs are in-cluster.
- Redirect URL `${PUBLIC_ORIGIN}/sso/callback`. Proxy prefix `/sso`.
- Reverse-proxy mode. Upstream `static://200`. Sets the `X-Auth-Request` headers.
- Accepts verified JWT bearer tokens. PKCE S256.
- Secure cookie with a `12h` lifetime. Any email domain.
- The current stable image, pinned.

**AuthorizationPolicy requirements:** action `CUSTOM`, provider `oauth2-proxy`, `targetRefs` the Gateway `platform-gateway` in `istio-ingress`, applied to every path except `/keycloak`, `/keycloak/*`, `/sso`, `/sso/*`, `/polaris` and `/polaris/*`. The bootstrap applies it only after the oauth2-proxy rollout succeeds.

- [ ] **Step 1: Write the failing checks in `validate.sh`.**
  - oauth2-proxy rollout and route Accepted.
  - `gateway::curl_anonymous /console/ -s -o /dev/null -w '%{http_code} %{redirect_url}'` gives `302` with a URL starting `$(origin::public)/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth`.
  - `gateway::curl /console/ -fsS -o /dev/null` succeeds.
  - `gateway::curl_anonymous /polaris/api/catalog/v1/config -s -o /dev/null -w '%{http_code}'` is `401`.
- [ ] **Step 2: Run them and see them fail.**

  Run: `KUBE_CONTEXT=retail-lakehouse bash platform/13-identity/validate.sh`

  Expected: FAIL on the oauth2-proxy rollout.

- [ ] **Step 3: Implement the manifests, the bootstrap additions and the `gateway.sh` changes.**
- [ ] **Step 4: Run the bootstrap, then validate, and see it pass.**
  1. Rerun the bootstrap and confirm the Secret `resourceVersion`s are unchanged.
  2. Run every wave validate that uses the gateway: `21-polaris`, `21-temporal`, `23-kafka-ui`, `23-kiali`, `25-lakehouse-control-plane` (each with `KUBE_CONTEXT=retail-lakehouse`).

  Expected: all pass with the gate on.
- [ ] **Step 5: Commit.** The README covers the gate, the ungated paths, the fail-closed behaviour and the break-glass (`kubectl port-forward` straight to a service).

```bash
git add platform/13-identity scripts/utils/gateway.sh
git commit -m "feat(platform): gate platform-gateway behind Keycloak via oauth2-proxy"
```

### Task 5: Trino without SOPS, logging in through Keycloak

**Files:**
- Modify: `platform/23-trino/values.yaml`, `platform/23-trino/bootstrap.sh`, `platform/23-trino/validate.sh`, `platform/23-trino/README.md`
- Delete: `platform/23-trino/values-secret.yaml`, `.sops.yaml`
- Modify: `tasks/apps.yml` and `taskfile.yml` (drop the `sops` precondition), `docs/prerequisites.md` (drop `sops` and the AGE setup)

**Interfaces:**
- Consumes: `identity/keycloak-clients` key `trino-client-secret` (Task 3), `object-storage/rustfs-secret` (`RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY`), `lakehouse-catalog/polaris-bootstrap-secret` (`credentials` = `realm,clientId,clientSecret`, read as in `25-lakehouse-control-plane/bootstrap.sh`), `lakehouse-query-engine/trino-keystore-password` (`password`), and `origin::public`.
- Produces: the Trino secrets and env vars in "Fixed names", set through the chart's top-level `env` so coordinator and workers both get them. `TRINO_POLARIS_CREDENTIAL` is `clientId:clientSecret`.

**Settings that move into `values.yaml`** (from the spec's inventory; values not shown here are the ones the spec lists):
- `server.coordinatorExtraConfig`:
  - HTTPS on 8443.
  - `http-server.https.keystore.path=/etc/trino/tls/keystore.p12`, `http-server.https.keystore.key=${ENV:TRINO_KEYSTORE_PASSWORD}`.
  - `http-server.https.truststore.path=/etc/trino/truststore/truststore.p12`, `http-server.https.truststore.key=${ENV:TRINO_KEYSTORE_PASSWORD}`.
  - `http-server.authentication.certificate.user-mapping.pattern=CN=([^,]+).*`.
  - `http-server.process-forwarded=true`.
  - `web-ui.authentication.type=oauth2`, plus the Keycloak OAuth2 lines:
    - `issuer=${ENV:PUBLIC_ORIGIN}/keycloak/realms/retail-lakehouse`
    - `auth-url=${ENV:PUBLIC_ORIGIN}/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth`
    - `token-url` and `jwks-url`: the in-cluster realm base followed by `/protocol/openid-connect/token` and `/protocol/openid-connect/certs`
    - `oidc.discovery=false`, `client-id=trino`, `client-secret=${ENV:TRINO_OAUTH2_CLIENT_SECRET}`, `principal-field=preferred_username`, `scopes=openid`

    Each OAuth2 line is prefixed with `http-server.authentication.oauth2.`.
- `server.exchangeManager`: `filesystem` with base dirs `s3://trino-fault-tolerance-nkm5,s3://trino-fault-tolerance-cws0`.
- `additionalConfigProperties`: `internal-communication.shared-secret=${ENV:TRINO_SHARED_SECRET}`, `retry-policy=TASK`, `tracing.enabled=true`, `tracing.exporter.endpoint=http://jaeger-collector.lakehouse-query-engine.svc.cluster.local:4317`.
- `additionalExchangeManagerProperties`: `exchange.s3.region=dummy-region`, the RustFS endpoint, `exchange.s3.aws-access-key=${ENV:TRINO_EXCHANGE_S3_ACCESS_KEY}`, `exchange.s3.aws-secret-key=${ENV:TRINO_EXCHANGE_S3_SECRET_KEY}`, `exchange.s3.path-style-access=true`.
- `catalogs.iceberg`: the twelve lines from the inventory, with `iceberg.rest-catalog.oauth2.credential=${ENV:TRINO_POLARIS_CREDENTIAL}`.
- No Google property remains. Delete the `values.yaml` comment that pointed at `values-secret.yaml`.

**Bootstrap requirements:** before `helm upgrade`, `bootstrap.sh`:
1. Creates `trino-internal-shared-secret` once.
2. Applies `trino-credentials` and ConfigMap `trino-public-origin` (key `origin`), both with the recommended labels, on every run.

`helm upgrade` takes only `--values values.yaml`.

- [ ] **Step 1: Write the failing checks in `validate.sh`.**
  - After the existing rollouts, the rendered `trino-coordinator` and `trino-catalog` ConfigMaps contain no secret value. Every `client-secret`, `shared-secret`, `.key`, `aws-*-key` and `oauth2.credential` property must be a `${ENV:` reference.
  - The coordinator's `config.properties` holds no `accounts.google.com`.
  - Check by property name only, never print a value.
- [ ] **Step 2: Run it and see it fail.**

  Run: `KUBE_CONTEXT=retail-lakehouse bash platform/23-trino/validate.sh`

  Expected: FAIL. Today's ConfigMaps hold plain values and Google.

- [ ] **Step 3: Implement.** Make the `values.yaml`, `bootstrap.sh`, deletion and precondition changes above. Update the README:
  - Remove the Prerequisites, First-time Setup and Secrets Management sections.
  - Authentication now reads mTLS for the CLI and Keycloak for the web UI.
  - Add a Secrets section listing the two Secrets and their sources.
- [ ] **Step 4: Bootstrap and check.**
  1. Run `KUBE_CONTEXT=retail-lakehouse bash platform/23-trino/bootstrap.sh`, then `validate.sh`. Expected: PASS, with coordinator and worker Running.
  2. Inside the coordinator, confirm `${ENV:…}` was substituted (Review Focus 3): `kubectl exec deployment/trino-coordinator --namespace lakehouse-query-engine --context retail-lakehouse -- trino --execute "SHOW CATALOGS"` lists `iceberg`. Then run `SELECT count(*) FROM iceberg.inventory.orders` and check it returns a number.
  3. Run `task trino-smoke-test KUBE_CONTEXT=retail-lakehouse` (mTLS) and `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh`. Expected: both pass.
- [ ] **Step 5: Commit.**

```bash
git add platform/23-trino tasks/apps.yml taskfile.yml docs/prerequisites.md
git rm platform/23-trino/values-secret.yaml .sops.yaml
git commit -m "feat(trino): log in through Keycloak and drop SOPS"
```

### Task 6: Trino web UI through the gateway

**Files:**
- Create: `platform/23-trino/trino-ui-route.yaml` (rendered with `envsubst` from `origin::public` at bootstrap, as `22-kafka-iceberg-connector` renders its image)
- Modify: `platform/23-trino/bootstrap.sh`, `platform/23-trino/validate.sh`, `platform/23-trino/README.md`, `platform/12-platform-gateway/README.md` (route table: `/keycloak`, `/sso`, `/ui`, `/oauth2`)

**Interfaces:**
- Consumes: `origin::public`, `gateway::curl`.
- Produces: HTTPRoute `trino-ui` in `lakehouse-query-engine`.
  - PathPrefix `/ui` and `/oauth2` to Service `trino` port 8080, with no rewrite.
  - A `RequestHeaderModifier` that sets `X-Forwarded-Proto: https`, plus `X-Forwarded-Host` and `X-Forwarded-Port` from the origin.
  - The namespace is allowed with `gateway::allow_routes lakehouse-query-engine`.

- [ ] **Step 1: Write the failing checks in `validate.sh`.**
  - `gateway::assert_routes_allowed lakehouse-query-engine` and the route Accepted.
  - `gateway::curl /ui/ -s -o /dev/null -w '%{http_code} %{redirect_url}'` gives a 3xx whose URL starts with `$(origin::public)/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth` and contains `redirect_uri=` with the encoded `$(origin::public)/oauth2/callback`.
- [ ] **Step 2: Run it and see it fail.** Expected: FAIL (no route).
- [ ] **Step 3: Implement the route, the bootstrap rendering and the README rows.**
- [ ] **Step 4: Run the bootstrap, then validate, and see it pass.** The gate's bearer token is not meant for Trino. If Trino answers it with 401 instead of the redirect, do two things:
  - Change the check to expect that 401, which still proves the route reaches Trino through the gate.
  - Note in the README that the Keycloak redirect is covered by the Task 7 browser check.
- [ ] **Step 5: Commit.**

```bash
git add platform/23-trino platform/12-platform-gateway/README.md
git commit -m "feat(trino): serve the web UI through platform-gateway"
```

### Task 7: Sizing, docs and clean rebuild

**Files:**
- Modify: the `13-identity` manifests (memory requests and limits), `platform/13-identity/README.md` (Memory section), `CLAUDE.md`

- [ ] **Step 1: Size the pods.** From Task 3 and Task 4 measurements and a 15 minute idle soak, set requests near measured usage and limits with headroom. Recompute node requested memory. If fewer than two Spark driver + executor pairs fit, stop and report.
- [ ] **Step 2: Update `CLAUDE.md`.**
  - Add a 2026-11-06 history line.
  - Deployed list: wave 12 gains `13-identity`.
  - Remove SOPS mentions from Platform and Trino text.
  - Ambient namespace list: add `identity`.
  - Known follow-ups: realm edits are manual on a running cluster; Polaris and workload identities are phase 3.
- [ ] **Step 3: Clean rebuild.** Run `task offboard KUBE_CONTEXT=retail-lakehouse`, then `task onboard KUBE_CONTEXT=retail-lakehouse`. Expected: every wave validates, including `13-identity`. Then run `task apps:validate KUBE_CONTEXT=retail-lakehouse` again. Expected: pass.
- [ ] **Step 4: Browser check over the Tailscale origin.** Close any tab the check opens.
  1. In a fresh profile, open `/console/tables?x=1`. Expected: the Keycloak login page.
  2. Log in as `platform-admin`. Expected: back on `/console/tables?x=1` (Review Focus 5).
  3. Open `/temporal`, `/kiali`, `/kafka-ui` and `/ui`. Expected: no second password prompt.
  4. Open the Polaris console at `/` and log in to Polaris (Review Focus 4).
- [ ] **Step 5: Commit, then report the manual step.** Afterwards the owner deletes the Google OAuth client in Google Cloud Console.

```bash
git add platform/13-identity CLAUDE.md
git commit -m "docs(platform): record Keycloak single sign-on and the clean rebuild"
```
