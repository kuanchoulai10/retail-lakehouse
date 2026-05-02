# Trino mTLS Authentication — Design

## Context

`23-trino` 目前 `authenticationType: "oauth2"`，透過 cert-manager 自簽 server cert 走 HTTPS 8443。OAuth2 設定為 Google OAuth client（`values-secret.yaml` SOPS 加密）。

實際使用時遇到問題：

- 從 `trino-coordinator` pod 內用 `trino` CLI 下 `SHOW CATALOGS` → HTTP 8080 被擋（`Authentication over HTTP is not enabled`）
- 改連 HTTPS 8443 → 自簽 cert 不被 Java truststore 信任（PKIX path building failed）
- 用 `--insecure` 跳過 TLS 驗證 → OAuth2 unauthorized（沒有 bearer token）

**需求**：

1. trino CLI（laptop） 與未來 in-cluster service 都能查詢 Trino，**不必經過 Google OAuth**
2. OAuth2 機制保留 — 給瀏覽器 Web UI（SSO）使用
3. 簽證設定統一 — server cert 與所有 client cert 由**同一個 cert-manager Issuer** 簽發

## Decisions

- **多重驗證**：`authenticationType: "certificate,oauth2"` — Trino 依序嘗試 client cert → OAuth2
- **PKI 範圍**：Trino-namespace 範圍。**bootstrap CA 階層**（`trino-selfsigned-issuer` 簽出 `trino-ca`，`trino-ca-issuer` 用該 CA secret 簽 server + client cert）。⚠️ 實作時發現：原本構想的「`trino-selfsigned-issuer` 同時簽 server 和 client」不成立 — `selfSigned` 不是 shared CA，每張 cert 自己當 root，導致 mTLS 雙向驗證失敗。標準 cert-manager pattern 需要 `isCA: true` 的中介 CA cert。
- **CN 格式**：`CN=<username>`（不加 `user/` 前綴）
- **Keystore 密碼**：所有 client cert 沿用既有 `trino-keystore-password` secret（值 `trinopassword`）
- **Truststore 建立**：新增獨立 init container 跑 `keytool` 把 `trino-tls-secret.ca.crt`（即 `trino-ca` 公鑰）包成 `truststore.p12`
- **Laptop cert 流程**：`task trino-client-cert USER=<name>` 一鍵簽發 + 匯出
- **Cert 期限**：Laptop client 365 天、CA 10 年、未來 in-cluster client 1 年
- **Output 路徑**：`23-trino/client-certs/<user>/`（**專案目錄內**，加進 `.gitignore`，不放家目錄）
- **mTLS server 端 properties 放置位置**：`server.coordinatorExtraConfig`（SOPS 加密的 `values-secret.yaml`，與 OAuth2 entries 並列）。⚠️ 原 spec 設想用明文 `additionalConfigProperties` (top-level)，但 chart 的 top-level `additionalConfigProperties` 同時套用 coordinator + worker，而 `http-server.authentication.*` 是 coordinator-only — worker 啟動時拒絕設定而 crash-loop。`coordinatorExtraConfig` 才是正確的目標位置。
- **In-cluster client 暫不實作**：留範本與決策樹，等真的有需求再開新 spec

## Architecture

### PKI 結構（trino namespace）— bootstrap CA 階層

```
Issuer: trino-selfsigned-issuer (selfSigned, bootstrap only)
  │
  └── Certificate: trino-ca (isCA: true, 10 年)
        └── Secret: trino-ca-secret      ← 含 CA private key + cert
              │
              ↓ 引用
        Issuer: trino-ca-issuer (ca:)    ← 真正在用的 issuer
              │
              ├── Certificate: trino-tls (server cert, 1 年)
              │     └── Secret: trino-tls-secret
              │           ├── tls.crt          ← server cert
              │           ├── tls.key
              │           ├── ca.crt           ← trino-ca 公鑰，建 truststore 用
              │           └── keystore.p12
              │
              └── Certificate: trino-client-<user> (client cert, 365 天)
                    └── Secret: trino-client-<user>-tls
                          ├── keystore.p12     ← client identity
                          ├── tls.crt
                          ├── tls.key
                          └── ca.crt           ← trino-ca 公鑰
```

關鍵：所有 server / client cert 的 `ca.crt` 欄位都是同一張 `trino-ca` 公鑰。Server truststore 和 laptop truststore 從各自 secret 的 `ca.crt` 建出來，內容相同 — 雙向 mTLS 驗證才能成立。

### 認證流程

```
trino-coordinator (HTTPS 8443)
  authenticationType: certificate,oauth2

  ① Client 帶 cert（laptop / in-cluster）
       trino CLI --keystore-path → 8443
       server 用 truststore 驗 cert → 過 → user-mapping 抽 CN → Trino user

  ② Client 不帶 cert（瀏覽器 SSO）
       browser → 8443 → 302 to Google → callback → bearer token → 過
```

## Components

### 變更（既有檔案）

| 檔案 | 變更 |
|---|---|
| `23-trino/values.yaml` | `authenticationType: "certificate,oauth2"`；新增 truststore + user-mapping properties；新增 init container 建 truststore |
| `23-trino/validate.sh` | 加 mTLS 設定靜態檢查 + negative test |
| `taskfile.yml` | 新 target `trino:client-cert`、`trino:smoke-test` |
| `.gitignore` | 加 `23-trino/client-certs/` |
| `23-trino/README.md` | 文件 mTLS 流程、瀏覽器 SSO manual checklist |

### 新增（檔案）

| 檔案 | 內容 |
|---|---|
| `23-trino/client-certificate-template.yaml` | `Certificate` CR 模板（用 `envsubst` 帶入 `${USER}`） |
| `23-trino/client-certs/<user>/` | 跑 `task trino:client-cert` 後產出（gitignore） |

## Server-Side 設定

### `values.yaml` 變更

```yaml
server:
  config:
    authenticationType: "certificate,oauth2"   # 從 "oauth2" 改

coordinator:
  additionalConfigProperties:
    - http-server.https.truststore.path=/etc/trino/truststore/truststore.p12
    - http-server.https.truststore.key=trinopassword
    - http-server.authentication.certificate.user-mapping.pattern=CN=([^,]+).*

  initContainers:
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
        - { name: tls-certs, mountPath: /tls-src, readOnly: true }
        - { name: tls-built, mountPath: /tls-built }
```

Volume 設計（避開既有 `tls-certs` 掛載點）：

- 新增 `emptyDir` volume `tls-built`
- Init container 寫入 `/tls-built/truststore.p12`
- Coordinator 主容器把 `tls-built` 掛到 **`/etc/trino/truststore/`**（**獨立路徑**，不和既有 `/etc/trino/tls/`（`tls-certs`）重疊）
- `additionalConfigProperties` 中對應改為：
  ```
  http-server.https.truststore.path=/etc/trino/truststore/truststore.p12
  ```

### Init container 整合

既有的「concat tls.key + tls.crt → trino-dev.pem」init container 定義在 SOPS-encrypted `values-secret.yaml`。新的 `build-truststore` 採**獨立**新增（不合併進去）：職責分離、image 不同（既有可能是 alpine、新的需 JRE）、好除錯。

### 設定放置位置

新的 `additionalConfigProperties` 條目（無祕密成分）放回明文 `values.yaml`，不進 SOPS encrypted 檔，讓變更可見。

### Rotation

cert-manager 自動 renew `trino-tls`，但 init container 不會重跑 → truststore.p12 不更新。對策：

- **MVP**：人工 `kubectl rollout restart deployment/trino-coordinator` 觸發
- **未來**：加 [stakater/Reloader](https://github.com/stakater/Reloader) annotation 自動 rolling restart

## Laptop Client Cert Flow

### `Certificate` CR 模板（`23-trino/client-certificate-template.yaml`）

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: trino-client-${USER}
  namespace: trino
spec:
  secretName: trino-client-${USER}-tls
  duration: 8760h         # 365 天
  renewBefore: 720h       # 30 天前 renew
  issuerRef:
    name: trino-selfsigned-issuer
    kind: Issuer
  commonName: ${USER}
  subject:
    organizations: [Trino]
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

### `taskfile.yml` 新 target

```yaml
trino:client-cert:
  desc: 'Issue Trino client cert. Usage: task trino:client-cert USER=alice'
  vars:
    OUTDIR: '23-trino/client-certs/{{.USER}}'
    CTX: '{{.KUBE_CONTEXT | default "mini"}}'
  cmds:
    - test -n "{{.USER}}" || (echo "ERROR: USER=<name> required"; exit 1)
    - mkdir -p {{.OUTDIR}} && chmod 700 {{.OUTDIR}}
    - USER={{.USER}} envsubst < 23-trino/client-certificate-template.yaml |
        kubectl apply -f - --context {{.CTX}}
    - kubectl wait --for=condition=Ready certificate/trino-client-{{.USER}}
        -n trino --timeout=120s --context {{.CTX}}
    - kubectl get -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}}
        -o jsonpath='{.data.keystore\.p12}' | base64 -d > {{.OUTDIR}}/keystore.p12
    - kubectl get -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}}
        -o jsonpath='{.data.ca\.crt}' | base64 -d > {{.OUTDIR}}/ca.crt
    - kubectl get -n trino secret trino-keystore-password --context {{.CTX}}
        -o jsonpath='{.data.password}' | base64 -d > {{.OUTDIR}}/password.txt
    - keytool -importcert -noprompt -alias trino-ca
        -file {{.OUTDIR}}/ca.crt
        -keystore {{.OUTDIR}}/truststore.p12
        -storetype PKCS12
        -storepass "$(cat {{.OUTDIR}}/password.txt)"
    - chmod 600 {{.OUTDIR}}/*
    - echo "✓ {{.OUTDIR}}/{keystore.p12, truststore.p12, password.txt}"
```

**Idempotent**：重跑會更新 Certificate CR、覆蓋本地檔。Cert-manager spec 沒變不會重簽；要強制 renew 用 `cmctl renew`。

### 使用範例（README）

```bash
# 1. 一次性簽 cert
task trino:client-cert USER=alice

# 2. port-forward（另開 terminal，留著）
kubectl port-forward -n trino svc/trino 8443:8443 --context retail-lakehouse

# 3. 查詢
trino \
  --server https://localhost:8443 \
  --user alice \
  --keystore-path 23-trino/client-certs/alice/keystore.p12 \
  --keystore-password "$(cat 23-trino/client-certs/alice/password.txt)" \
  --truststore-path 23-trino/client-certs/alice/truststore.p12 \
  --truststore-password "$(cat 23-trino/client-certs/alice/password.txt)" \
  --execute "SHOW CATALOGS"
```

### 環境假設

- Laptop 已裝 `kubectl`、`task`、`envsubst`（`brew install gettext`）
- Laptop 已裝 Java（trino CLI 本來就要 JRE，所以 `keytool` 必有）
- KUBE_CONTEXT 已設為 `retail-lakehouse`

## In-Cluster Client Cert Pattern（範本，不實作）

目前無 in-cluster service 在查 Trino。Spec 留範本給未來新增服務時參考。

### 範本（namespace=trino 內的服務）

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: trino-client-catalog-browser
  namespace: trino
spec:
  secretName: trino-client-catalog-browser-tls
  duration: 8760h
  commonName: catalog-browser
  issuerRef:
    name: trino-selfsigned-issuer
    kind: Issuer
  usages: [client auth]
  keystores:
    pkcs12:
      create: true
      passwordSecretRef:
        name: trino-keystore-password
        key: password
```

Deployment 掛 secret：

```yaml
spec:
  containers:
    - name: app
      env:
        - name: TRINO_KEYSTORE_PATH
          value: /etc/trino-client/keystore.p12
        - name: TRINO_KEYSTORE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: trino-keystore-password
              key: password
      volumeMounts:
        - { name: trino-client, mountPath: /etc/trino-client, readOnly: true }
  volumes:
    - name: trino-client
      secret:
        secretName: trino-client-catalog-browser-tls
```

### 限制：cross-namespace

`trino-selfsigned-issuer` 是 namespace-scoped，只能被 `trino` namespace 內的 Certificate 引用。如果未來其他 namespace（例：`spark`、`catalog-browser` 各自獨立 namespace）也需要 client cert，要在新 spec 中決定：

- **(a)** 升級成 `ClusterIssuer`（範圍從 trino-only 擴展到全 cluster）
- **(b)** 用 [stakater/Reflector](https://github.com/emberstack/kubernetes-reflector) 把 secret 複製到目標 namespace
- **(c)** 在每個目標 namespace 也建一個 `Issuer`，但要共用同一張 CA private key

**這次不做**。

## Testing

### `validate.sh` 增量檢查（自動化、快速）

```bash
echo "==> Validating mTLS config: truststore exists in coordinator"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  test -s /etc/trino/truststore/truststore.p12

echo "==> Validating mTLS config: authentication.type includes certificate"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.type=certificate,oauth2$' /etc/trino/config.properties

echo "==> Validating mTLS config: user-mapping pattern set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.certificate.user-mapping.pattern=' /etc/trino/config.properties

echo "==> Validating mTLS config: truststore path set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.https.truststore.path=' /etc/trino/config.properties

echo "==> Validating server rejects unauthenticated HTTPS"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  curl -sk -o /dev/null -w "%{http_code}" https://localhost:8443/v1/statement -X POST -d 'SELECT 1' \
  | grep -qE '^(401|403)$'
```

### Smoke test（`task trino:smoke-test`，獨立 target，不自動跑）

```yaml
trino:smoke-test:
  desc: 'End-to-end mTLS smoke test using a throwaway client cert'
  vars:
    USER: 'smoke-test'
    OUTDIR: '23-trino/client-certs/smoke-test'
    CTX: '{{.KUBE_CONTEXT | default "mini"}}'
  cmds:
    - task: trino:client-cert
      vars: { USER: '{{.USER}}' }
    - kubectl port-forward -n trino svc/trino 18443:8443 --context {{.CTX}} &
    - sleep 2
    - |
      trino --server https://localhost:18443 --user {{.USER}} \
        --keystore-path {{.OUTDIR}}/keystore.p12 \
        --keystore-password "$(cat {{.OUTDIR}}/password.txt)" \
        --truststore-path {{.OUTDIR}}/truststore.p12 \
        --truststore-password "$(cat {{.OUTDIR}}/password.txt)" \
        --execute "SHOW CATALOGS"
    - pkill -f 'port-forward.*trino' || true
    - kubectl delete -n trino certificate trino-client-{{.USER}} --context {{.CTX}} --ignore-not-found
    - kubectl delete -n trino secret trino-client-{{.USER}}-tls --context {{.CTX}} --ignore-not-found
    - rm -rf {{.OUTDIR}}
```

### OAuth2 path（manual checklist in README）

> ✅ After deploy, open `https://localhost:8443/ui` in browser, expect Google SSO redirect, login successfully, see Trino Web UI.

無法寫 shell 自動化（需要瀏覽器 + Google account）。

## Open Questions / Future Work

- **Cross-namespace client cert**：未來若有非 `trino` namespace 的服務要查 Trino，需新 spec 決定 ClusterIssuer / Reflector / per-namespace Issuer
- **Auto rolling-restart on cert renewal**：目前需要人工 `kubectl rollout restart`，未來可加 stakater/Reloader
- **Cert revocation**：cert-manager 無原生 CRL/OCSP 支援，目前靠短效期 + 換 Issuer 撤銷整批；如果要做即時 revocation 需要另外設計
- **CI smoke test**：`trino:smoke-test` 目前手動跑，未來可考慮加進 GitHub Actions

## Out of Scope

- 替換 OAuth2 provider（仍用 Google）
- 升級 Issuer 為 ClusterIssuer
- 實際簽發 in-cluster service 的 client cert
- Cross-namespace cert 流通機制
- 自動化 OAuth2 SSO 端對端測試
