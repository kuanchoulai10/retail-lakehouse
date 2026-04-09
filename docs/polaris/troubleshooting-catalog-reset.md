# Troubleshooting: Catalog Reset After Polaris Restart

每次重啟 Apache Polaris 後，catalog 設定就消失了？這是正常行為，本文說明原因，以及如何快速重建所有設定。

---

## 為什麼 Polaris 重啟後會「失憶」？

Apache Polaris 預設使用 **in-memory persistence**，所有的 catalog、namespace、table registration 都存在記憶體中。一旦 Pod 重啟，這些狀態就會完全清空。

你可以在 Polaris 的設定中看到這個行為：

```yaml
persistence:
  type: in-memory
```

!!! warning "In-Memory Persistence 的限制"
    In-memory 模式適合本地開發和測試，但**不適合生產環境**。每次 Pod 重啟（包括 rollout、OOMKill、節點調度）都會導致 catalog 狀態全部消失。如果需要持久化，請改用 Eclipse Link 搭配外部資料庫。

---

## 重啟後哪些東西會消失？

Polaris 重啟後，以下設定會全部重置：

| 元件 | 狀態 |
|---|---|
| **Catalog** (`iceberg`) | 消失，需重建 |
| **Warehouse 路徑** | 消失，需重新設定指向 MinIO |
| **Namespace** (`inventory`) | 消失，需重建 |
| **Table Registration** | 消失，需從 metadata 重新 register |
| **Principal Role 授權** | 消失，需重新 grant |

MinIO 上的實際資料檔案（Parquet、metadata JSON）**不受影響**——S3 的資料是持久的，只是 Polaris 不再知道這些表格存在而已。

!!! tip "好消息"
    由於 MinIO 上的 metadata 檔案都還在，重建 catalog 只需要重新「告訴 Polaris 去哪裡找資料」，不需要重新寫入或移動任何資料。

---

## Bootstrap 步驟：重建 Catalog 設定

以下步驟假設你已經有一個正在運行的 Polaris 服務，並且 MinIO 上的資料完好。

### Step 1：取得 OAuth2 Token

Polaris 使用 OAuth2 client credentials flow 做認證。先用 root 帳號取得 access token：

```bash
curl -s -X POST \
  http://localhost:8181/api/catalog/management/v1/oauth/tokens \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=root&client_secret=secret&scope=PRINCIPAL_ROLE:ALL"
```

成功回應範例：

```json
{
  "access_token": "<YOUR_JWT_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

把 token 存起來，後續步驟都會用到：

```bash
TOKEN="<YOUR_JWT_TOKEN>"
```

---

### Step 2：建立 Catalog（指向 MinIO）

建立名為 `iceberg` 的 catalog，warehouse 路徑指向 MinIO 上的 S3 bucket：

```bash
curl -s -X POST \
  http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iceberg",
    "type": "INTERNAL",
    "properties": {
      "default-base-location": "s3://retail-lakehouse-7dj2/warehouse/"
    },
    "storageConfigInfo": {
      "storageType": "S3",
      "allowedLocations": ["s3://retail-lakehouse-7dj2/warehouse/"],
      "s3.endpoint": "http://minio-api.minio.svc.cluster.local:9000",
      "s3.pathStyleAccess": "true"
    }
  }'
```

!!! warning "pathStyleAccess: true 是必要的"
    如果忘記設定 `s3.pathStyleAccess: true`，Polaris 在嘗試 register table 時會發生 `UnknownHostException`。這是因為 MinIO 預設使用 path-style URL（`http://minio:9000/bucket/key`），而不是 virtual-hosted style（`http://bucket.minio:9000/key`）。後者在本地叢集中無法解析，導致 DNS 查找失敗。詳見下方的 [常見錯誤排查](#_6)。

---

### Step 3：授予 service_admin 對 Catalog 的管理權限

Polaris 重啟後，principal role 的授權也會消失。需要重新把 `catalog_admin` role grant 給 `service_admin`：

```bash
curl -s -X PUT \
  http://localhost:8181/api/management/v1/principal-roles/service_admin/catalog-roles/iceberg/catalog_admin \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

成功時回傳 HTTP 201，無 body。

---

### Step 4：建立 Namespace

在 `iceberg` catalog 下建立 `inventory` namespace：

```bash
curl -s -X POST \
  http://localhost:8181/api/catalog/v1/iceberg/namespaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": ["inventory"],
    "properties": {
      "location": "s3://retail-lakehouse-7dj2/warehouse/inventory"
    }
  }'
```

---

### Step 5：Register 現有的 Table

MinIO 上已有資料，只需要告訴 Polaris metadata 檔案在哪裡。先確認 metadata 路徑：

```bash
# 用 mc 列出最新的 metadata 檔案
mc ls minio/retail-lakehouse-7dj2/warehouse/inventory/<table_name>/metadata/ \
  --recursive | sort | tail -5
```

然後 register table：

```bash
curl -s -X POST \
  http://localhost:8181/api/catalog/v1/iceberg/namespaces/inventory/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "products",
    "metadata-location": "s3://retail-lakehouse-7dj2/warehouse/inventory/products/metadata/00003-abc12345.metadata.json"
  }'
```

!!! tip "確認 metadata 路徑"
    `metadata-location` 必須指向最新的 `.metadata.json` 檔案（通常是編號最大的那個），否則 Polaris 可能會載入舊版的 schema 或 snapshot。

對每一張需要恢復的 table 重複此步驟。

---

## 驗證 Catalog 是否正常

完成上述步驟後，確認 catalog 和 table 都可以正常查詢：

```bash
# 列出所有 namespaces
curl -s \
  http://localhost:8181/api/catalog/v1/iceberg/namespaces \
  -H "Authorization: Bearer $TOKEN"

# 列出 inventory namespace 下的 tables
curl -s \
  http://localhost:8181/api/catalog/v1/iceberg/namespaces/inventory/tables \
  -H "Authorization: Bearer $TOKEN"
```

---

## 常見錯誤排查

### UnknownHostException：table registration 失敗

**錯誤訊息：**

```
java.net.UnknownHostException: retail-lakehouse-7dj2.minio-api.minio.svc.cluster.local
```

**原因：** Polaris 嘗試使用 virtual-hosted style URL，把 bucket name 放到 hostname 前面，導致 DNS 查找失敗。

**解法：** 確認 catalog 建立時有設定 `"s3.pathStyleAccess": "true"`（參見 Step 2）。如果 catalog 已存在但設定錯誤，需要刪除後重建：

```bash
# 刪除舊的 catalog
curl -s -X DELETE \
  http://localhost:8181/api/management/v1/catalogs/iceberg \
  -H "Authorization: Bearer $TOKEN"

# 重新執行 Step 2，加上 pathStyleAccess
```

### 401 Unauthorized

Token 已過期（預設 1 小時）。重新執行 Step 1 取得新的 token。

### Namespace 已存在

如果 namespace 已存在（有時重啟後部分狀態殘留），POST 會回傳 409 Conflict，可以忽略此錯誤直接繼續 Step 5。

---

## 未來改善方向

如果 catalog reset 問題影響開發效率，可以考慮以下方向：

- **改用持久化後端**：設定 `persistence.type: eclipse-link` 搭配 PostgreSQL，catalog 狀態就能在重啟後保留
- **自動化 bootstrap script**：將以上 curl 指令包裝成 shell script 或 Kubernetes Job，在 Polaris Pod ready 後自動執行
- **Health check integration**：在 CI/CD pipeline 加入 catalog 驗證步驟，確保每次部署後 catalog 都正確設定
