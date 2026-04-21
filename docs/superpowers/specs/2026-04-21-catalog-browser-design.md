# Catalog Browser — Read-Only Iceberg Metadata API

## Context

retail-lakehouse 定位為「Data 的 GitHub」DataOps SaaS 平台。使用者需要透過前端 UI 瀏覽 Iceberg table 的 metadata，包含 catalogs、namespaces、tables、branches、tags、snapshots。

本設計為第一批 read-only API，透過 PyIceberg 連接 Polaris REST catalog 取得 metadata。

## Decisions

- **放在現有 `table-maintenance` backend** — 擴展現有服務，不另建 bounded context。
- **PyIceberg 作為 metadata 查詢方式** — Python native，對 branches/tags/snapshots 支援最完整，與 FastAPI 整合自然。
- **簡化架構，不套完整 DDD** — 純 read-only metadata 透傳，不建 domain model / use case / port。未來有寫入操作時再引入。
- **設定加到現有 `AppSettings`** — 只需 `iceberg_catalog_uri` 和 `iceberg_catalog_name` 兩個 field。

## API Endpoints

所有 endpoints 皆為 `GET`，read-only。

```
GET /v1/catalogs/{catalog}/namespaces
GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables
GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}
GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots
GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches
GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags
```

### Response Examples

**GET /v1/catalogs/{catalog}/namespaces**
```json
{
  "namespaces": ["default", "raw", "curated"]
}
```

**GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables**
```json
{
  "tables": ["orders", "products", "inventory"]
}
```

**GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}**
```json
{
  "table": "orders",
  "namespace": "default",
  "location": "s3://warehouse/default/orders",
  "current_snapshot_id": 123456789,
  "schema": {
    "fields": [
      {"id": 1, "name": "order_id", "type": "long", "required": true},
      {"id": 2, "name": "customer_id", "type": "long", "required": true},
      {"id": 3, "name": "total", "type": "decimal(10,2)", "required": false}
    ]
  },
  "properties": {
    "write.format.default": "parquet",
    "commit.retry.num-retries": "4"
  }
}
```

**GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots**
```json
{
  "snapshots": [
    {
      "snapshot_id": 123456789,
      "parent_id": null,
      "timestamp_ms": 1713600000000,
      "operation": "append",
      "summary": {
        "added-data-files": "3",
        "added-records": "1500",
        "total-records": "1500",
        "total-data-files": "3"
      }
    }
  ]
}
```

**GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches**
```json
{
  "branches": [
    {
      "name": "main",
      "snapshot_id": 123456789,
      "max_snapshot_age_ms": null,
      "max_ref_age_ms": null,
      "min_snapshots_to_keep": null
    }
  ]
}
```

**GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags**
```json
{
  "tags": [
    {
      "name": "v1.0",
      "snapshot_id": 123456789,
      "max_ref_age_ms": null
    }
  ]
}
```

## Architecture

```
adapter/inbound/web/catalog/       — FastAPI routes + response DTOs
adapter/outbound/catalog/          — PyIceberg client wrapper
dependencies/                      — catalog client DI (FastAPI Depends)
configs/                           — AppSettings iceberg fields
```

### Adapter — Outbound (PyIceberg Client Wrapper)

`adapter/outbound/catalog/iceberg_catalog_client.py`:
- 封裝 PyIceberg `load_catalog()` 與 table metadata 查詢
- 提供 methods: `list_namespaces()`, `list_tables()`, `load_table()`, `list_snapshots()`, `list_branches()`, `list_tags()`
- 將 PyIceberg 物件轉換為 plain dict/dataclass，不讓 PyIceberg 型別洩漏到 route 層

### Adapter — Inbound (FastAPI Routes)

每個 endpoint 一個 file（遵循既有 one-object-per-file 慣例）：
- `adapter/inbound/web/catalog/list_namespaces.py`
- `adapter/inbound/web/catalog/list_tables.py`
- `adapter/inbound/web/catalog/get_table.py`
- `adapter/inbound/web/catalog/list_snapshots.py`
- `adapter/inbound/web/catalog/list_branches.py`
- `adapter/inbound/web/catalog/list_tags.py`
- `adapter/inbound/web/catalog/dto.py` — response models

### Dependencies

`dependencies/catalog.py`:
- 提供 `get_catalog_client()` dependency，從 `AppSettings` 讀取 catalog URI/name
- 使用 `@lru_cache` 或 app lifespan 管理 catalog 連線

### Configuration

`AppSettings` 新增：
```python
iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
iceberg_catalog_name: str = "iceberg"
```

## Dependencies (pyproject.toml)

新增 `pyiceberg` dependency：
```toml
pyiceberg = ">=0.9"
```

PyIceberg 的 REST catalog support 已內建，不需額外 extras。

## Error Handling

- Catalog 不存在 / 連線失敗 → 502 Bad Gateway
- Namespace 不存在 → 404 Not Found
- Table 不存在 → 404 Not Found
- PyIceberg 例外統一在 route 層 catch，轉換為適當的 HTTP status code

## Testing Strategy

- **Outbound adapter 測試：** mock PyIceberg catalog 物件，驗證 wrapper 的轉換邏輯
- **Inbound adapter 測試：** 使用 httpx `TestClient`，mock outbound catalog client，驗證 route 行為與 response 格式
- **Settings 測試：** 驗證新 field 的預設值與環境變數覆蓋

## Task Breakdown

每個 task 獨立可驗證、可 commit：

| # | Task | Scope | Verification |
|---|------|-------|-------------|
| 1 | AppSettings 加 iceberg fields | configs + test | pytest |
| 2 | PyIceberg catalog client wrapper | outbound adapter + test | pytest (mock catalog) |
| 3 | GET /namespaces endpoint | inbound route + DI + test | pytest (httpx) |
| 4 | GET /tables endpoint | inbound route + test | pytest |
| 5 | GET /table metadata endpoint | inbound route + test | pytest |
| 6 | GET /snapshots endpoint | inbound route + test | pytest |
| 7 | GET /branches endpoint | inbound route + test | pytest |
| 8 | GET /tags endpoint | inbound route + test | pytest |
