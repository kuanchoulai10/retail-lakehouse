# Polaris 權限模型

Polaris 的權限系統分三層，控制誰能對哪些資源做什麼操作。

## 權限架構

```
Principal (root)
  └─ PrincipalRole (service_admin)
       └─ CatalogRole (catalog_admin)
            └─ Grant (privilege + scope)
```

| 層級 | 說明 |
|------|------|
| **Principal** | 身份（例如 `root`），對應 OAuth2 的 `client_id` |
| **PrincipalRole** | 角色群組，一個 principal 可有多個 role |
| **CatalogRole** | Catalog 層級的角色，定義對特定 catalog 的權限 |
| **Grant** | 具體的權限授予，綁定在 CatalogRole 上 |

## Grant 類型與 Privilege

每個 grant 有兩個維度：**scope（作用範圍）** 和 **privilege（操作權限）**。

### Scope

| type | 說明 | 作用範圍 |
|------|------|---------|
| `catalog` | Catalog 層級 | 整個 catalog 的所有 namespace 和 table |
| `namespace` | Namespace 層級 | 指定 namespace 下的所有 table |

### Privilege

| Privilege | Scope | 說明 |
|-----------|-------|------|
| `CATALOG_MANAGE_ACCESS` | catalog | 管理 catalog 的權限設定（建立/刪除 catalog role、授予 grant） |
| `CATALOG_MANAGE_METADATA` | catalog | 管理 catalog 的 metadata（建立/刪除 namespace、table） |
| `TABLE_READ_DATA` | namespace | 讀取 table 的完整 metadata（schema、snapshots、refs） |
| `TABLE_WRITE_DATA` | namespace | 寫入 table（commit snapshot） |

!!! warning "CATALOG_MANAGE_METADATA ≠ TABLE_READ_DATA"

    `CATALOG_MANAGE_METADATA` 允許 list namespaces 和 list tables（因為這些是 catalog 層級的操作），但**不允許 load table**（讀取 table 的 schema、snapshots、refs）。

    Load table 需要 `TABLE_READ_DATA`，這是 namespace 層級的 grant，必須額外授予。

    這是最常見的權限問題：能看到 table 列表，但讀不了 table 內容。

## 查看目前的權限

### 查看 CatalogRole 列表

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8181/api/management/v1/catalogs/iceberg/catalog-roles \
  | python3 -m json.tool
```

### 查看 CatalogRole 的 Grants

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8181/api/management/v1/catalogs/iceberg/catalog-roles/catalog_admin/grants \
  | python3 -m json.tool
```

??? info "預設 catalog_admin 的 grants"

    ```json
    {
        "grants": [
            {"privilege": "CATALOG_MANAGE_ACCESS", "type": "catalog"},
            {"privilege": "CATALOG_MANAGE_METADATA", "type": "catalog"}
        ]
    }
    ```

    注意：只有 catalog 層級的 manage 權限，沒有 table 的讀寫權限。

## 授予 TABLE_READ_DATA

對特定 namespace 授予讀取權限：

```bash
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8181/api/management/v1/catalogs/iceberg/catalog-roles/catalog_admin/grants" \
  -d '{
    "grant": {
      "privilege": "TABLE_READ_DATA",
      "type": "namespace",
      "namespace": ["inventory"]
    }
  }'
```

授予後，`catalog_admin` 可以對 `inventory` namespace 下的所有 table 做 `load_table`，包含讀取 schema、snapshots、branches、tags。

### 驗證

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8181/api/management/v1/catalogs/iceberg/catalog-roles/catalog_admin/grants \
  | python3 -m json.tool
```

??? info "授予後的 grants"

    ```json
    {
        "grants": [
            {"privilege": "CATALOG_MANAGE_ACCESS", "type": "catalog"},
            {"privilege": "CATALOG_MANAGE_METADATA", "type": "catalog"},
            {"privilege": "TABLE_READ_DATA", "type": "namespace", "namespace": ["inventory"]}
        ]
    }
    ```

## 常見問題

### `not authorized for op LOAD_TABLE_WITH_READ_DELEGATION`

```
Principal 'root' with activated PrincipalRoles '[service_admin]' and activated grants via
'[service_admin, catalog_admin]' is not authorized for op LOAD_TABLE_WITH_READ_DELEGATION
```

**原因：** 缺少 `TABLE_READ_DATA` grant。`catalog_admin` 預設只有 catalog 層級的 manage 權限。

**解法：** 授予 `TABLE_READ_DATA` 在目標 namespace 上（見上方）。

### 新增 namespace 後也要授權

`TABLE_READ_DATA` 是 per-namespace 的 grant。如果之後建立了新的 namespace（例如 `raw`），需要再執行一次授權：

```bash
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8181/api/management/v1/catalogs/iceberg/catalog-roles/catalog_admin/grants" \
  -d '{
    "grant": {
      "privilege": "TABLE_READ_DATA",
      "type": "namespace",
      "namespace": ["raw"]
    }
  }'
```

### PyIceberg 連線需要的最小權限

table-maintenance-backend 透過 PyIceberg 連接 Polaris，各 endpoint 需要的權限：

| 操作 | 需要的 Privilege |
|------|-----------------|
| List namespaces | `CATALOG_MANAGE_METADATA` |
| List tables | `CATALOG_MANAGE_METADATA` |
| Load table (metadata, schema) | `TABLE_READ_DATA` |
| List snapshots | `TABLE_READ_DATA` |
| List branches / tags | `TABLE_READ_DATA` |
