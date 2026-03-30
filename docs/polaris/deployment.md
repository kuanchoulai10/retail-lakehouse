# Apache Polaris Deployment

Apache Polaris is an open-source Iceberg REST catalog. It manages metadata for Iceberg tables (namespaces, schemas, table locations) and issues vended credentials to clients so they can read and write data files directly on object storage. In this project, Polaris acts as the catalog layer sitting between MinIO (storage) and query engines like Trino.

!!! info "Polaris 在整個架構中的角色"

    Polaris 本身**不存資料**，也不做 query。它只存 catalog metadata，然後幫 Trino 和 Kafka Iceberg connector 發放「臨時通行證」(vended credentials) 去直接讀寫 MinIO。

    整個流程長這樣：

    1. Trino 向 Polaris 拿 token（OAuth2 client_credentials）
    2. Trino 問 Polaris：`orders` 這張表在哪？schema 是什麼？
    3. Polaris 回傳 table location（例如 `s3://retail-lakehouse-7dj2/warehouse/retail/orders/`）和 vended credentials
    4. Trino 拿著 vended credentials 直接連 MinIO 讀寫 Parquet 檔

    Polaris 只在步驟 2–3 介入，不參與實際資料傳輸。

## Prerequisites

Before deploying, create the two Kubernetes secrets that Polaris needs:

```bash
# 1. MinIO credentials for vended credentials issuance
kubectl create namespace polaris --context mini
kubectl create secret generic polaris-storage-secret \
  --from-literal=awsAccessKeyId=minio_user \
  --from-literal=awsSecretAccessKey=minio_password \
  -n polaris --context mini

# 2. Bootstrap credentials for the initial admin principal
#    Format: <realm>,<username>,<password>
kubectl create secret generic polaris-bootstrap-secret \
  --from-literal=credentials="POLARIS,root,secret" \
  -n polaris --context mini
```

!!! info "什麼是 Bootstrap Credentials"

    Polaris 啟動時需要一個初始管理員帳號（root principal），才能登入後做後續設定（建 catalog、授權等）。

    `POLARIS_BOOTSTRAP_CREDENTIALS` 環境變數指定這組帳號，格式是 `realm,username,password`。

    - **realm**：Polaris 內的隔離命名空間（預設 `POLARIS`）
    - **username / password**：root principal 的 client ID 和 client secret

    如果沒有設定這個環境變數，Polaris 會**自動生成一組隨機帳號**並把它印在 pod log 裡，格式是：

    ```
    realm: POLARIS root principal credentials: b65181da2cd9dba7:5bc240fcb49f808f94becdd811bc721f
    ```

    自動生成的帳號每次重啟都不同，所以建議明確設定以保持可預期。

## Helm Chart

The official Polaris Helm chart is published at `https://downloads.apache.org/incubator/polaris/helm-chart`. This URL is a valid Helm repository index but `helm search repo` does not detect it automatically due to index format differences. Use the direct `.tgz` URL instead:

```bash
# This does NOT work reliably:
helm repo add polaris https://downloads.apache.org/incubator/polaris/helm-chart
helm search repo polaris  # returns no results

# Use the direct tgz URL instead:
helm show values \
  https://downloads.apache.org/incubator/polaris/helm-chart/1.3.0-incubating/polaris-1.3.0-incubating.tgz
```

!!! info "為什麼 helm search 找不到"

    Helm repository 的 `index.yaml` 裡，chart 的下載路徑是相對路徑（`1.3.0-incubating/polaris-1.3.0-incubating.tgz`），而不是完整 URL。Helm CLI 在解析時可能無法正確組合完整路徑，導致 `helm search` 和 `helm show values` 都失效。解法是直接用完整 URL 指向 `.tgz` 檔案。

To see all default values:

```bash
helm show values \
  https://downloads.apache.org/incubator/polaris/helm-chart/1.3.0-incubating/polaris-1.3.0-incubating.tgz \
  > 21-polaris/values-default.yaml
```

The default values are saved to `21-polaris/values-default.yaml` for reference.

## values.yaml Walkthrough

Our `values.yaml` only overrides the fields that matter. Below is the full file with explanations for each section.

### Image

```yaml
image:
  repository: apache/polaris
  tag: "1.3.0-incubating"
  pullPolicy: IfNotPresent
```

Pin the image tag. The default is `latest`, which is not reproducible.

### Persistence

```yaml
persistence:
  type: in-memory
```

!!! warning "in-memory 的代價"

    `in-memory` 代表所有 catalog metadata（catalog 定義、namespace、table 清單）都只存在 pod 的記憶體中。**Pod 重啟後，所有狀態清空**，需要重新建立 catalog。

    這在開發環境下可以接受，但在生產環境必須換成 `relational-jdbc`，搭配外部 PostgreSQL：

    ```yaml
    persistence:
      type: relational-jdbc
      relationalJdbc:
        secret:
          name: polaris-postgres-secret  # 含 jdbcUrl, username, password
    ```

### Storage Secret

```yaml
storage:
  secret:
    name: polaris-storage-secret
    awsAccessKeyId: awsAccessKeyId
    awsSecretAccessKey: awsSecretAccessKey
```

This tells Polaris which Kubernetes secret to use when issuing vended credentials. The `awsAccessKeyId` and `awsSecretAccessKey` values are the **key names** inside the secret, not the actual credentials.

!!! info "storage.secret 和 extraEnv 的差別"

    這兩個地方都設定了 MinIO 帳密，用途不同：

    | 設定位置 | 用途 |
    |---------|------|
    | `storage.secret` | Polaris 在發放 vended credentials 時，把這組帳密包在 credential response 裡給客戶端（Trino）用 |
    | `extraEnv.AWS_ACCESS_KEY_ID` | AWS SDK 本身在發 STS 請求時用的預設帳密，也決定 Polaris server process 自身的 S3 認證 |

    兩者都要設定，缺一不可。

### Environment Variables

```yaml
extraEnv:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: polaris-storage-secret
        key: awsAccessKeyId
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: polaris-storage-secret
        key: awsSecretAccessKey
  - name: AWS_REGION
    value: "dummy-region"
  - name: AWS_ENDPOINT_URL_S3
    value: "http://minio-api.minio.svc.cluster.local:9000"
  - name: AWS_ENDPOINT_URL_STS
    value: "http://minio-api.minio.svc.cluster.local:9000"
  - name: POLARIS_BOOTSTRAP_CREDENTIALS
    valueFrom:
      secretKeyRef:
        name: polaris-bootstrap-secret
        key: credentials
```

!!! info "為什麼需要 AWS_REGION"

    Polaris 內部使用 AWS SDK v2。這個 SDK 在任何 S3/STS 操作前都要求設定 region，否則拋出：

    ```
    Unable to load region from any of the providers in the chain
    ```

    MinIO 本身不需要 region，但 SDK 需要。設成任意字串（如 `dummy-region`）即可讓 SDK 通過 region 驗證。

!!! info "AWS_ENDPOINT_URL_S3 vs AWS_ENDPOINT_URL_STS"

    AWS SDK v2 支援這兩個環境變數，用於把 API 請求導向非 AWS 的端點（例如 MinIO）：

    - `AWS_ENDPOINT_URL_S3`：導向 MinIO 的 S3 API（讀寫物件、列出 bucket）
    - `AWS_ENDPOINT_URL_STS`：導向 MinIO 的 STS API（發放臨時 credential）

    兩個都指向同一個 MinIO endpoint，因為 MinIO 同時實作 S3 和 STS 兩套 API。

!!! warning "不要把 MinIO endpoint 放在 advancedConfig"

    一個常見的錯誤是試圖用 `advancedConfig` 設定 MinIO endpoint：

    ```yaml
    # 這樣寫會讓 Polaris 無法啟動！
    advancedConfig:
      polaris.storage.s3.endpoint: "http://minio-api..."
      polaris.storage.s3.path-style-access: "true"
    ```

    `advancedConfig` 只接受 Polaris 或 Quarkus 本身定義的 configuration property key。`polaris.storage.s3.endpoint` 不是有效的 key，Polaris 啟動時會報：

    ```
    Configuration validation failed:
      SRCFG00050: polaris.storage.s3.endpoint ... does not map to any root
    ```

    然後進入 CrashLoopBackOff。**正確做法是用 `extraEnv` 設定 `AWS_ENDPOINT_URL_S3`。**

### Authentication

```yaml
authentication:
  type: internal
  tokenBroker:
    type: rsa-key-pair
    maxTokenGeneration: PT1H
    secret:
      name: ~
```

!!! info "tokenBroker.secret.name 是什麼"

    Polaris 使用 RSA key pair 來簽發和驗證 JWT token（客戶端拿 token 來呼叫 catalog API）。

    - `secret.name: ~`（空值）：Polaris 每次啟動時自動生成一對新的 RSA 密鑰。Pod 重啟後，之前發出的 token 全部失效，客戶端需要重新取得 token。**開發環境下可以接受。**
    - `secret.name: <secret-name>`：指向一個存有固定 RSA key pair 的 K8s Secret，重啟後 token 仍然有效。**生產環境建議使用。**

## Installation

```bash
bash 21-polaris/install.sh
```

The installation script performs these steps:

1. Create the `polaris` namespace
2. Create `polaris-storage-secret` with MinIO credentials
3. Create `polaris-bootstrap-secret` with bootstrap credentials
4. Deploy Polaris via Helm using the direct `.tgz` URL

??? info "install.sh"

    ```bash
    --8<-- "./retail-lakehouse/21-polaris/install.sh"
    ```

## Verifying the Deployment

Check that the pod is running:

```bash
kubectl get all -n polaris --context mini
```

??? info "Result"

    ```
    NAME                          READY   STATUS    RESTARTS   AGE
    pod/polaris-67c5c4767-846k2   1/1     Running   0          2m12s

    NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
    service/polaris        ClusterIP   10.100.227.14   <none>        8181/TCP   9m23s
    service/polaris-mgmt   ClusterIP   None            <none>        8182/TCP   9m23s

    deployment.apps/polaris   1/1     1            1           9m23s
    ```

Check the health endpoint:

```bash
kubectl port-forward svc/polaris-mgmt 8182:8182 -n polaris --context mini &
curl http://localhost:8182/q/health
```

??? info "Result"

    ```json
    {
        "status": "UP",
        "checks": [
            {
                "name": "Database connections health check",
                "status": "UP"
            }
        ]
    }
    ```

Check the startup logs to confirm bootstrap credentials were applied:

```bash
kubectl logs -l app.kubernetes.io/name=polaris -n polaris --context mini
```

If `POLARIS_BOOTSTRAP_CREDENTIALS` was set correctly, you will see:

```
INFO Bootstrapping realm(s) 'POLARIS', if necessary, from root credentials set provided
     via the environment variable POLARIS_BOOTSTRAP_CREDENTIALS ...
```

If the env var was missing or the secret did not exist, Polaris auto-generates credentials and prints them:

```
realm: POLARIS root principal credentials: b65181da2cd9dba7:5bc240fcb49f808f94becdd811bc721f
```

!!! warning "Production Readiness Warnings"

    Polaris prints several warnings on startup in the development configuration. These are expected and can be ignored for local development:

    ```
    ⚠️ A public key file wasn't provided and will be generated.
    ⚠️ A private key file wasn't provided and will be generated.
    ⚠️ The realm context resolver is configured to map requests without a realm header to the default realm.
    ⚠️ The current metastore is intended for tests only.
    ```

    Each warning points to a specific configuration option that should be hardened before going to production. See the [Polaris production configuration guide](https://polaris.apache.org/in-dev/unreleased/configuring-polaris-for-production) for details.

## Cleanup

```bash
bash 21-polaris/uninstall.sh
kubectl delete namespace polaris --context mini
```
