# Keycloak single sign-on for the platform UIs

## Intent

Every web UI of the platform sits behind one gateway (`platform-gateway`, path routing since 2026-11-05) and is reached mostly over Tailscale (`tailscale serve` → port-forward :8591). Today the UIs have no login at all (console, Temporal UI, Kiali, Kafka UI) or their own (Trino: Google OAuth2). The owner wants one login, done once, after which every UI is usable, and wants that login to come from a Keycloak deployed by the platform's own waves instead of Google.

This is phases 1 and 2 of a longer path:

1. Keycloak plus a login gate on the gateway in front of every UI.
2. Trino's web UI logs in through Keycloak instead of Google; Google is removed.
3. (Later, separate design) workloads (Trino, Spark maintenance, Iceberg sink, table-maintenance) get their own Keycloak identities and Polaris accepts Keycloak tokens, then per-service permissions, possibly via OPA as in Bloomberg's Iceberg Summit 2026 talk and the Polaris Keycloak + OPA guide.

## Goals

- A Keycloak realm, its database, users and clients are created by `task onboard KUBE_CONTEXT=retail-lakehouse` with no manual clicks.
- Opening any gateway path without a session leads to the Keycloak login page; after logging in once, the browser returns to the page it asked for, and every other UI opens without another password prompt.
- Logged-in users can use every UI fully (no per-service roles yet: everyone who can log in can do everything each UI allows today).
- Trino's web UI (`/ui`) is reachable through the gateway and logs in through Keycloak; its Google OAuth2 configuration is gone.
- Trino CLI and `e2e.sh` keep working unchanged through the client-certificate (mTLS) path on port-forward :8443.
- Every `validate.sh` that checks a gateway path still passes with the gate on, and `apps:validate` can be rerun at any time.

## Non-goals

- Per-service authorization (Trino access rules, Kafka UI roles, Temporal namespace permissions, Kiali modes).
- Multi-tenancy. Dropped as a direction, not just deferred.
- Polaris authentication changes and workload identities (phase 3).
- Single logout across services, MFA, social login, self-registration.
- Authentication on the table-maintenance API for callers that do not go through the gateway (worker, Spark callback): unchanged.
- Making the Polaris console spike (outside the repo, `~/Projects/polaris-tools/local`) part of a wave.

## Anti-goals

- A login that works only from one origin by accident, or depends on hand edits to the running cluster.
- Breaking the in-cluster paths: nothing that talks pod-to-pod (Trino → Polaris, Iceberg sink, worker, Spark) may start needing a Keycloak token in this design.
- Keeping two login systems for Trino's UI (Google and Keycloak) side by side.

## Constraints

- Project rules in `CLAUDE.md` apply: wave layout (`bootstrap.sh` + `validate.sh`, `KUBE_CONTEXT` required), Kubernetes label standard enforced by `scripts/check_k8s_labels.py` (including pod `app.kubernetes.io/version` = image tag), every new application namespace created in the ambient mesh (`namespace::apply_ambient`) and allowed on the gateway (`gateway::allow_routes`), no explanatory comments in YAML, images pinned to exact versions.
- Secrets: generated once at bootstrap and stored in Kubernetes Secrets with a NotFound-only check plus `kubectl create` (the `table-maintenance-db` pattern, not the `polaris-token-broker` one), never printed, never committed. SOPS is removed (see below).
- Gateway API CRDs are the standard channel (no `TLSRoute`, no `BackendTLSPolicy`); TLS ends at `tailscale serve`, and everything behind it is plain HTTP.
- Node memory: about 62% used, about 76% of allocatable requested. New pods must leave room for two concurrent Spark maintenance driver + executor pairs (see the node memory follow-up in `CLAUDE.md`); size requests from measured usage, not equal to limits.

## Decisions

**Public origin.** Login has one public origin: the Tailscale URL that fronts the gateway (today `https://kcls-mac-mini.tail46ae98.ts.net:8591`). Keycloak's frontend hostname, oauth2-proxy's redirect URL and Trino's callback all use it. The value is not hard-coded in manifests (owner's decision). The bootstrap detects it from `tailscale status` (this machine's MagicDNS name, `https://`, port `:8591`). `PUBLIC_ORIGIN=https://…` overrides it on `task onboard` and on the wave scripts. If neither yields a value, the bootstrap fails fast; there is no localhost fallback. Because the realm import runs only once, changing the origin on a running cluster means updating the realm by hand or a re-onboard (README). Plain `http://localhost:8591` still reaches the gateway, but logging in from it is not a goal.

**Issuer split.** Tokens carry the public issuer (`<origin>/keycloak/realms/<realm>`). Pods cannot rely on resolving the Tailscale name, so in-cluster consumers (oauth2-proxy, Trino) fetch token and JWKS endpoints from Keycloak's in-cluster Service while validating against the public issuer (Keycloak backchannel enabled for dynamic hostnames; explicit endpoints on the consumers rather than discovery). The Polaris guide's `--resolve` workaround exists for this same mismatch.

**Components** (all in one new namespace `identity`, ambient, gateway routes allowed, in one new wave `13-identity` so the gate exists before any later wave validates through the gateway):

- `keycloak-db`: PostgreSQL, same pattern as `temporal-db` / `table-maintenance-db` (Recreate strategy, PVC).
- `keycloak`: the official image as a plain Deployment, served under `/keycloak` on the gateway (relative path set in Keycloak itself, like the other apps), proxy headers trusted from the gateway, health and metrics enabled. The realm comes from a realm JSON in the wave imported at startup; import only creates a missing realm, so later realm edits on a running cluster are manual or need a re-onboard (documented in the wave README).
- `oauth2-proxy`: the official image, provider Keycloak OIDC, its own endpoints under `/sso` (not the default `/oauth2`, which Trino's own OAuth2 callback uses), cookie secure, session in the cookie (no Redis).
- The gate: an Istio `extensionProviders` entry (HTTP ext_authz to oauth2-proxy) in `platform/12-istiod/values.yaml`, and an `AuthorizationPolicy` with action `CUSTOM` targeting `platform-gateway`, created by `13-identity` after oauth2-proxy is ready.

**Realm content.** One realm `retail-lakehouse` with:

- a confidential client for oauth2-proxy,
- a confidential client for Trino,
- a confidential client for validation scripts (client credentials grant, see below),
- one human user `platform-admin` (my call) with a generated password in a Secret, read by the owner with `kubectl`.

Client secrets and the user password are generated at bootstrap; the realm JSON references them, or the bootstrap sets them after import (builder's choice).

**Gate scope.** Every gateway path requires a session except:

- `/keycloak` and `/sso` (the login flow itself),
- `/polaris` (an API with its own Polaris tokens; the Polaris console spike sends `Authorization: Bearer <Polaris token>`, which the gate must not reject).

The Polaris console page at `/` stays gated like any other page. An unauthenticated browser request gets a redirect to the login page, not a bare 401/403.

**Validation through the gate.** `gateway::curl` obtains a token for the validation client from Keycloak's token endpoint (through the gateway's ungated `/keycloak` path) and sends it as a bearer token that oauth2-proxy accepts. Validation scripts keep their current checks. Before `13-identity` exists (a fresh onboard below wave 13) the helper works without a token.

**Trino.**

- An HTTPRoute in `23-trino` sends `/ui` and `/oauth2` to the coordinator's HTTP port 8080, without rewriting.
- Trino processes forwarded headers (`http-server.process-forwarded=true`). The gateway route must deliver `X-Forwarded-Proto: https` and the public host and port, because Envoy sees plain HTTP from the port-forward.
- Trino's OAuth2 points at Keycloak (public issuer, in-cluster token and JWKS endpoints) with the principal from `preferred_username`. Because the browser already holds a Keycloak session from the gate, this second OAuth2 round trip completes without a password prompt.
- Authentication type stays `certificate,oauth2`, so mTLS on :8443 is unchanged. Keycloak's Trino client also allows `https://localhost:8443/oauth2/callback`, so the existing port-forward UI keeps working.
- Trino reads its Keycloak client secret from an environment variable sourced from a Kubernetes Secret.
- The Google OAuth2 properties are dropped when the Trino settings move out of the SOPS file.

**Retiring Google.** After phase 2 works, the Google OAuth client in Google Cloud Console is deleted by the owner (manual step, listed in the README).

## Settled after the builder check (my calls)

- **SOPS is removed from the project (owner's decision).** With Google gone, nothing needs a committed encrypted secret: like every other wave, Trino's secrets are created at `task onboard` and disappear with `task offboard`.
  - `platform/23-trino/values-secret.yaml` and `.sops.yaml` are deleted. Their non-secret settings (exchange manager, catalogs, mTLS truststore, user-mapping) move into `values.yaml`.
  - Each secret value comes from a Kubernetes Secret through an environment variable (Trino `${ENV:…}`). There are three sources:
    - an existing Secret, such as the RustFS credentials or the Polaris client credentials;
    - a Secret generated once at bootstrap, such as the internal shared secret;
    - the Keycloak client secret for Trino.
  - The `sops` precondition in `tasks/apps.yml` and `taskfile.yml`, the `sops -d` in `23-trino/bootstrap.sh`, and the SOPS, AGE and helm-secrets sections in `23-trino/README.md` and `docs/prerequisites.md` are removed. Historical plans and specs stay as they are.
  - The owner never runs `sops`. The current content was read once on 2026-11-06 through a redacting script, with the owner's approval. Inventory:

    | Where | Non-secret content (moves to `values.yaml` as is) | Secret, and its new source |
    |---|---|---|
    | `server.coordinatorExtraConfig` | HTTPS on 8443, keystore path `/etc/trino/tls/keystore.p12`, truststore path `/etc/trino/truststore/truststore.p12`, certificate user-mapping `CN=([^,]+).*` | keystore and truststore passwords: the existing `trino-keystore-password` Secret |
    | | Google OAuth2 issuer, client-id, scopes, `principal-field=email`, `web-ui.authentication.type=oauth2`: **dropped**, replaced by the Keycloak OAuth2 lines | Google client secret: **dropped**; the Keycloak client secret comes from `13-identity` |
    | `server.exchangeManager` | `filesystem`, two `s3://trino-fault-tolerance-*` base dirs | none |
    | `additionalConfigProperties` | `retry-policy=TASK`, tracing to the Jaeger collector | `internal-communication.shared-secret`: generated once at bootstrap |
    | `additionalExchangeManagerProperties` | region, RustFS endpoint, path-style access | S3 access and secret key: the existing RustFS credentials |
    | `catalogs.iceberg` | REST catalog URI, warehouse `iceberg`, `OAUTH2`, scope `PRINCIPAL_ROLE:ALL`, `vended-credentials-enabled=true`, native S3, region, path-style, RustFS endpoint | `iceberg.rest-catalog.oauth2.credential`: the existing Polaris client credentials |

  - Secrets reach Trino as `${ENV:…}` from `secretKeyRef`, not through a file-based secrets provider. Trino's only file option is a PKCS12 secrets keystore, documented for 484 while we run 476, and it needs its own password from an environment variable anyway. A side benefit: these values no longer sit in plain text in the Helm-rendered `trino-coordinator` / `trino-catalog` ConfigMaps, where they are today.
- **Trino HTTP port:** the `trino` Service already exposes `http` 8080 (checked on the running cluster), so no new listener is needed. Routing to it with `process-forwarded=true` is accepted. The `/ui` and `/oauth2` route sets `X-Forwarded-Proto: https` and the public host and port with a `RequestHeaderModifier`, because Envoy only sees plain HTTP from the port-forward.
- **Gate coverage:** one `CUSTOM` policy covers the whole gateway, with only the listed exceptions. New UIs, including spikes on `/`, are gated by default and register nothing.
- **Expired sessions:** after the session expires, a background `fetch` may fail until the page is reloaded. That is accepted. The session lifetime is long enough for a working day (builder picks the exact value). There are no separate 401-versus-redirect rules.
- **Keycloak or oauth2-proxy down:** the gate fails closed. The break-glass is `kubectl port-forward` straight to a service, which bypasses the gateway. The `13-identity` README says so.
- **Memory:** Keycloak is sized small (bounded JVM heap). If the measured total would leave room for fewer than two Spark driver + executor pairs, the builder stops and reports instead of trimming other pods.

## Left to the builder

- Versions of Keycloak, oauth2-proxy and PostgreSQL (current stable, pinned).
- Exact ext_authz header lists, oauth2-proxy flags and how the redirect-on-deny is achieved, as long as the behaviour above holds.
- Memory requests and limits, from measured usage.
- Whether the realm import references secrets through placeholders or the bootstrap patches clients after import.
- README content for `13-identity`, and updates to `12-istiod`, `12-platform-gateway` (route table), `23-trino` and `CLAUDE.md` (deployed list, history line).

## Verification

- A clean `task offboard` + `task onboard KUBE_CONTEXT=retail-lakehouse` passes with every wave validated, including `13-identity`.
- `apps:validate` passes when rerun.
- HBONE holds in `identity`.
- In a browser over the Tailscale origin:
  - opening `/console/` without a session shows the Keycloak login;
  - after logging in, `/console`, `/temporal`, `/kiali`, `/kafka-ui` and `/ui` (Trino) all open with no second password prompt;
  - the Polaris console at `/` still logs in to Polaris.
- `trino` CLI with a client certificate on :8443 and `e2e.sh` pass.
- No `sops` call is left in the deploy path, and Trino has no Google OAuth2 properties.
