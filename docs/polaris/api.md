# Interacting with Apache Polaris

Polaris exposes two distinct APIs on two distinct ports. Understanding which API to use, and when, is the key to working with Polaris effectively.

| API | Port | Purpose |
|-----|------|---------|
| **Management API** | `8181` | Admin operations: create/delete catalogs, manage principals, assign roles |
| **Iceberg REST API** | `8181` | Catalog operations: create namespaces, create/read/write Iceberg tables |
| **Management service** | `8182` | Health checks (`/q/health`) and Prometheus metrics |

!!! info "兩套 API，同一個 port"

    Management API 和 Iceberg REST API 都在 port 8181，但 URL prefix 不同：

    - Management API：`/api/management/v1/...`
    - Iceberg REST API：`/api/catalog/v1/...`

    區別很重要：建立 catalog 是 Management API 的工作；Trino 和 Kafka connector 與 Polaris 互動走的是 Iceberg REST API。

## Port Forward

All examples in this article use a local port-forward. Run this before executing any `curl` commands:

```bash
kubectl port-forward svc/polaris 8181:8181 -n polaris --context mini &
```

## Authentication

Both APIs require a Bearer token. Polaris uses the OAuth2 `client_credentials` flow.

```bash
curl -s -X POST http://localhost:8181/api/catalog/v1/oauth/tokens \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=root&client_secret=secret&scope=PRINCIPAL_ROLE:ALL"
```

??? info "Result"

    ```json
    {
        "access_token": "<JWT_TOKEN>",
        "token_type": "bearer",
        "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "expires_in": 3600
    }
    ```

Save the token for reuse:

```bash
TOKEN=$(curl -s -X POST http://localhost:8181/api/catalog/v1/oauth/tokens \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=root&client_secret=secret&scope=PRINCIPAL_ROLE:ALL" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

!!! info "client_id 和 client_secret 的來源"

    這就是部署時在 `polaris-bootstrap-secret` 裡設定的值。格式是 `realm,username,password`，其中：

    - `username` → `client_id`
    - `password` → `client_secret`

    如果是自動生成的帳號（沒有設定 bootstrap secret），從 pod log 找到 credentials 行：
    ```
    realm: POLARIS root principal credentials: b65181da2cd9dba7:5bc240fcb49f808f94becdd811bc721f
    ```
    這裡 `b65181da2cd9dba7` 是 `client_id`，`5bc240fcb49f808f94becdd811bc721f` 是 `client_secret`。

!!! info "scope=PRINCIPAL_ROLE:ALL 是什麼"

    Polaris 的 token scope 格式是 `PRINCIPAL_ROLE:<role_name>`，代表取得特定 principal role 的授權。

    `PRINCIPAL_ROLE:ALL` 是 root principal 專用，代表取得所有權限。一般 service account 應該只取它被授予的 role。

## Management API

### Create a Catalog

A catalog is the top-level unit in Polaris. It maps to a storage location on MinIO.

```bash
curl -s -X POST http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iceberg",
    "type": "INTERNAL",
    "properties": {
      "default-base-location": "s3://retail-lakehouse-7dj2/warehouse"
    },
    "storageConfigInfo": {
      "storageType": "S3",
      "allowedLocations": ["s3://retail-lakehouse-7dj2/"],
      "pathStyleAccess": true
    }
  }'
```

??? info "Result"

    ```json
    {
        "type": "INTERNAL",
        "name": "iceberg",
        "properties": {
            "default-base-location": "s3://retail-lakehouse-7dj2/warehouse"
        },
        "createTimestamp": 1774886190664,
        "storageConfigInfo": {
            "pathStyleAccess": true,
            "storageType": "S3",
            "allowedLocations": [
                "s3://retail-lakehouse-7dj2/warehouse",
                "s3://retail-lakehouse-7dj2/"
            ]
        }
    }
    ```

!!! info "storageConfigInfo 的欄位"

    | 欄位 | 說明 |
    |------|------|
    | `storageType` | 必填。支援 `S3`、`GCS`、`AZURE`、`FILE`。MinIO 用 `S3`。 |
    | `allowedLocations` | Polaris 允許存取的 S3 路徑清單。Table location 必須在這個範圍內，否則 Polaris 拒絕操作。 |
    | `default-base-location` | 建立 namespace / table 時，如果沒有指定 location，預設用這個路徑加上資源名稱。 |
    | `pathStyleAccess` | Boolean。設 `true` 啟用 path-style URL（MinIO 必須）。**注意：這是頂層 boolean 欄位，不是 `s3.pathStyleAccess` 字串。** |
    | `roleArn` | AWS IAM Role ARN，用於 STS AssumeRole。MinIO 不用 IAM，**省略這個欄位**，不要設空字串（會報錯）。 |

!!! warning "pathStyleAccess 欄位格式"

    `pathStyleAccess` 是 `S3StorageConfigInfo` 的頂層 boolean 欄位。使用字串 `"s3.pathStyleAccess": "true"` 會被 Polaris 忽略，導致 Polaris 以 virtual-hosted style 存取 MinIO，產生：

    ```
    UnknownHostException: <bucket-name>.<minio-endpoint>
    ```

    正確寫法是 `"pathStyleAccess": true`（boolean，不帶引號，不加 `s3.` prefix）。

!!! warning "roleArn: \"\" 會報錯"

    如果把 `roleArn` 設成空字串，Polaris 會回傳：
    ```json
    {"error": {"message": "ARN must not be empty", "code": 400}}
    ```
    MinIO 不使用 IAM Role，正確做法是**完全省略** `roleArn` 欄位。

### List Catalogs

```bash
curl -s http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Delete a Catalog

```bash
curl -s -X DELETE http://localhost:8181/api/management/v1/catalogs/iceberg \
  -H "Authorization: Bearer $TOKEN"
```

## Iceberg REST API

The Iceberg REST API is what Trino and the Kafka Iceberg connector use. Polaris follows the [Iceberg REST Catalog spec](https://github.com/apache/iceberg/blob/main/open-api/rest-catalog-open-api.yaml).

### Discover the Catalog Prefix

Before calling any Iceberg REST endpoints, fetch the config to find the catalog `prefix`. Polaris uses the catalog name as the prefix, embedded in every subsequent URL:

```bash
curl -s "http://localhost:8181/api/catalog/v1/config?warehouse=iceberg" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

??? info "Result"

    ```json
    {
        "defaults": {
            "default-base-location": "s3://retail-lakehouse-7dj2/warehouse"
        },
        "overrides": {
            "prefix": "iceberg"
        },
        "endpoints": [
            "GET /v1/{prefix}/namespaces",
            "POST /v1/{prefix}/namespaces",
            "GET /v1/{prefix}/namespaces/{namespace}/tables",
            "POST /v1/{prefix}/namespaces/{namespace}/tables",
            "..."
        ]
    }
    ```

!!! info "prefix 的作用"

    `overrides.prefix` 的值（這裡是 `iceberg`）會被嵌入後續所有 Iceberg REST API 的 URL 路徑，格式是：

    ```
    /api/catalog/v1/{prefix}/namespaces
    /api/catalog/v1/{prefix}/namespaces/{namespace}/tables
    ```

    這個設計允許一個 Polaris 實例同時服務多個 catalog，每個 catalog 有自己的 prefix 作為隔離。

    Trino 在設定 Iceberg catalog 時，會先呼叫這個 config endpoint 取得 prefix，然後用它組合後續的 API 路徑。

### List Namespaces

```bash
curl -s "http://localhost:8181/api/catalog/v1/iceberg/namespaces" \
  -H "Authorization: Bearer $TOKEN"
```

??? info "Result"

    ```json
    {"namespaces": [], "next-page-token": null}
    ```

### Create a Namespace

```bash
curl -s -X POST "http://localhost:8181/api/catalog/v1/iceberg/namespaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace": ["retail"], "properties": {}}'
```

??? info "Result"

    ```json
    {
        "namespace": ["retail"],
        "properties": {
            "location": "s3://retail-lakehouse-7dj2/warehouse/retail/"
        }
    }
    ```

    Polaris 自動根據 catalog 的 `default-base-location` 計算出 namespace 的 storage path。

### Create a Table

Creating a table is the first operation that triggers a real S3 write — Polaris writes the initial metadata file to MinIO.

```bash
curl -s -X POST "http://localhost:8181/api/catalog/v1/iceberg/namespaces/retail/tables" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "orders",
    "schema": {
      "type": "struct",
      "schema-id": 0,
      "fields": [
        {"id": 1, "name": "id",     "required": true,  "type": "long"},
        {"id": 2, "name": "amount", "required": false, "type": "double"}
      ]
    },
    "write-order": {"order-id": 0, "fields": []},
    "stage-create": false
  }'
```

!!! info "Table 建立時發生什麼事"

    呼叫 `POST /namespaces/{ns}/tables` 之後，Polaris 會做以下幾件事：

    1. 在 in-memory store 記錄 table metadata（schema、partition spec 等）
    2. 決定 table 的 storage location（例如 `s3://retail-lakehouse-7dj2/warehouse/retail/orders/`）
    3. 呼叫 AWS SDK，在 MinIO 的對應路徑寫入初始的 `metadata.json` 檔案
    4. 把 table location 和 vended credentials 回傳給呼叫方

    步驟 3 是 Polaris **第一次實際連接 MinIO** 的時機。如果 `AWS_REGION`、`AWS_ENDPOINT_URL_S3` 沒有正確設定，這一步就會失敗：

    ```json
    {
        "error": {
            "message": "Failed to get subscoped credentials: Unable to load region from any of the providers",
            "code": 422
        }
    }
    ```

    這個錯誤代表 Polaris pod 裡缺少 `AWS_REGION` 環境變數。

### List Tables

```bash
curl -s "http://localhost:8181/api/catalog/v1/iceberg/namespaces/retail/tables" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

??? info "Result"

    ```json
    {
        "identifiers": [
            {"namespace": ["retail"], "name": "orders"}
        ]
    }
    ```

### Get Table Metadata

```bash
curl -s "http://localhost:8181/api/catalog/v1/iceberg/namespaces/retail/tables/orders" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

The response includes the full table metadata: schema, partition spec, sort order, snapshot history, and the `metadata-location` pointing to the metadata file on MinIO.

## MinIO Connectivity: When Does Polaris Actually Connect?

Polaris does **not** maintain a persistent connection to MinIO. It connects to MinIO only at specific moments:

| Operation | Does Polaris touch MinIO? |
|-----------|--------------------------|
| Start up | No |
| Create catalog | No (only validates config) |
| Create namespace | No |
| Create table | **Yes** — writes initial `metadata.json` |
| Update table (commit) | **Yes** — writes new metadata snapshot |
| Read table metadata | No (reads from in-memory store) |
| Client requests vended credentials | **Yes** — calls STS to generate temporary credentials |

!!! info "Vended Credentials 是什麼"

    Vended credentials 是 Polaris 代替客戶端（Trino）向 STS 取得的**臨時存取金鑰**，有效期通常是 1 小時。

    流程：

    1. Trino 要讀 `retail.orders` 這張表
    2. Trino 向 Polaris 的 Iceberg REST API 請求 table metadata
    3. Polaris 的 response 裡包含 `credentials` 欄位：
       ```json
       {
         "credentials": {
           "access_key_id": "...",
           "secret_access_key": "...",
           "session_token": "..."
         }
       }
       ```
    4. Trino 用這組臨時金鑰直接連 MinIO 讀取 Parquet 檔案
    5. Polaris 不參與實際的資料傳輸

    這個設計的好處是客戶端不需要持有 MinIO root 密碼，只拿得到時效性的臨時金鑰，每次操作都要重新向 Polaris 取得。

## Polaris URL Summary

```
Port 8181 (main):
  POST /api/catalog/v1/oauth/tokens          → Get auth token
  GET  /api/catalog/v1/config?warehouse=X    → Discover catalog prefix

  Management API (/api/management/v1/):
    POST   /catalogs                          → Create catalog
    GET    /catalogs                          → List catalogs
    DELETE /catalogs/{name}                   → Delete catalog

  Iceberg REST API (/api/catalog/v1/{prefix}/):
    GET    /namespaces                        → List namespaces
    POST   /namespaces                        → Create namespace
    DELETE /namespaces/{ns}                   → Delete namespace
    GET    /namespaces/{ns}/tables            → List tables
    POST   /namespaces/{ns}/tables            → Create table
    GET    /namespaces/{ns}/tables/{table}    → Get table metadata
    DELETE /namespaces/{ns}/tables/{table}    → Drop table

Port 8182 (management, headless service):
  GET /q/health                               → Health check
  GET /q/metrics                              → Prometheus metrics
```
