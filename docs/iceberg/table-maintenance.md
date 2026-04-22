# Iceberg Table Maintenance

Apache Iceberg 的表維護指南 — 從「為什麼需要維護」到「怎麼在這個專案裡跑它」。

---

## 為什麼 Iceberg 表需要維護

Iceberg 的核心設計是**不可變檔案（immutable files）**。每一次寫入都會：

1. 建立一個或多個新的 Parquet 資料檔
2. 更新 manifest 檔案，記錄哪些資料檔屬於這張表
3. 提交一個新的 **snapshot**，讓整張表「前進」到新狀態

這個設計帶來了 time travel、ACID 交易、concurrent reads/writes 等好處，但也帶來了一個現實問題：**隨著時間過去，表的目錄裡會累積大量的小檔案**。

```
warehouse/
  inventory/orders/
    data/
      00001.parquet   ← 第 1 次寫入
      00002.parquet   ← 第 2 次寫入
      00003.parquet   ← 第 3 次寫入
      ...
      00500.parquet   ← 第 500 次寫入
```

查詢引擎掃描 500 個小檔案，遠比掃描 5 個大檔案慢。這不是 Iceberg 的 bug，而是需要定期執行**維護作業**來解決的取捨。

---

## 四個主要維護程序

Iceberg 提供了四個 SQL stored procedures，透過 `CALL` 語法執行：

| 程序 | 作用 |
|---|---|
| `rewrite_data_files` | 將多個小 Parquet 檔合併成較大的檔案（compaction） |
| `expire_snapshots` | 刪除舊的 snapshot 並回收不再被參照的資料檔 |
| `remove_orphan_files` | 清理沒有被任何 snapshot 參照的孤立檔案 |
| `rewrite_manifests` | 整理 manifest 檔案，加快 query planning 速度 |

這四個程序共同維持表的健康狀態，缺一不可。

---

## `rewrite_data_files`：Compaction 的核心

### 它做了什麼

`rewrite_data_files` 的工作流程：

1. 讀取符合條件的多個小 Parquet 檔
2. 將它們合併成較大、接近目標大小（預設 512 MB）的新檔案
3. 提交一個新的 Iceberg snapshot，讓表指向新的檔案
4. **舊的檔案不會立即刪除** — 它們仍被舊 snapshot 參照，需要等 `expire_snapshots` 才會真正清除

!!! info "舊檔案的生命週期"
    `rewrite_data_files` 完成後，舊的小檔案並不消失。它們被舊 snapshot 保護著，讓 time travel 查詢仍可讀取歷史資料。只有在執行 `expire_snapshots` 並讓舊 snapshot 過期後，這些檔案才會被標記為可刪除。

### 三種 Strategy

#### BIN-PACK（預設）

純粹依照**檔案大小**做 compaction。把太小的檔案（低於 `min-file-size-bytes`）和其他檔案打包成接近 `target-file-size-bytes` 的大檔案。不改變資料順序。

適用時機：大多數情況下的定期維護。

#### SORT

在合併的同時，依照指定欄位對資料**排序**。查詢時如果常用該欄位過濾，排序後的檔案可以讓 Spark 跳過更多 row groups（data skipping）。

```sql
CALL retail.system.rewrite_data_files(
  table => 'retail.inventory.orders',
  strategy => 'sort',
  sort_order => 'zorder(order_date, customer_id)'
)
```

#### ZORDER

**多維度排序**，適合查詢條件同時涉及多個欄位的情況。Z-order 曲線讓相關的資料在多個維度上都盡量相鄰，提升多欄位過濾的效率。

!!! tip "Strategy 選擇建議"
    不確定要用哪個？從 **BIN-PACK** 開始。它最快、最安全。只有在你確認查詢有特定欄位過濾的熱點，且 BIN-PACK 後效果不夠理想，才考慮 SORT 或 ZORDER。

### CALL SQL 語法完整說明

```sql
CALL retail.system.rewrite_data_files(
  table   => 'retail.inventory.orders',   -- (1)
  strategy => 'binpack',                  -- (2)
  options  => map(                        -- (3)
    'rewrite-all',   'true',              -- (4)
    'target-file-size-bytes', '536870912' -- (5)
  )
)
```

**(1) `table`** — 要 compact 的表，格式為 `<catalog>.<namespace>.<table>`。

**(2) `strategy`** — `binpack`、`sort` 或 `zorder`，預設 `binpack`。

**(3) `options => map(...)`** — 以 key-value pairs 傳入調校參數。

**(4) `rewrite-all`** — 設為 `true` 時，強制重寫**所有**資料檔，不管它們是否已經達到目標大小。適合首次維護或手動觸發的完整 compaction。預設 `false`。

**(5) `target-file-size-bytes`** — 目標檔案大小（bytes），預設 `536870912`（512 MB）。

### 其他常用 Options

| Option | 預設值 | 說明 |
|---|---|---|
| `min-file-size-bytes` | 75% of target | 小於此大小的檔案才會被納入 compaction |
| `max-file-size-bytes` | 180% of target | 大於此大小的檔案不會被重寫 |
| `min-input-files` | 5 | 一個 file group 至少要有幾個檔案才觸發重寫 |
| `max-concurrent-file-group-rewrites` | 1 | 同時執行的 file group 數量 |
| `partial-progress.enabled` | false | 啟用後，每批次提交獨立 snapshot，避免大型 job 全失敗 |
| `partial-progress.max-commits` | 10 | 搭配上方選項，最多幾個批次 |

### 回傳結果

`rewrite_data_files` 執行完成後會回傳一個 DataFrame，包含：

| 欄位 | 說明 |
|---|---|
| `rewritten_data_files_count` | 被合併掉的原始檔案數量 |
| `added_data_files_count` | 新寫出的檔案數量 |
| `rewritten_bytes_count` | 重寫了多少 bytes |
| `failed_data_files_count` | 失敗的檔案數（partial progress 模式下才有意義） |

---

## 其他三個維護程序

### `expire_snapshots`

```sql
CALL retail.system.expire_snapshots(
  table       => 'retail.inventory.orders',
  older_than  => TIMESTAMP '2025-01-01 00:00:00',
  retain_last => 5
)
```

刪除 `older_than` 時間點之前的 snapshot，但至少保留最新的 `retain_last` 個（預設 1）。快照被刪除後，只被那些快照參照的資料檔也會從 metadata 中移除，物理刪除則由 FileIO 完成。

!!! warning "執行順序很重要"
    先跑 `rewrite_data_files`，再跑 `expire_snapshots`。反過來可能導致 compaction job 讀不到它需要的舊版檔案。

**可用環境變數（`GLAC_` 前綴）：**

| 環境變數 | 說明 |
|---|---|
| `GLAC_EXPIRE_SNAPSHOTS__TABLE` | 目標表 |
| `GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN` | ISO-8601 時間戳，刪除此時間前的 snapshot |
| `GLAC_EXPIRE_SNAPSHOTS__RETAIN_LAST` | 至少保留最新幾個 snapshot，預設 1 |
| `GLAC_EXPIRE_SNAPSHOTS__MAX_CONCURRENT_DELETES` | 並行刪除數 |
| `GLAC_EXPIRE_SNAPSHOTS__STREAM_RESULTS` | 串流模式回傳結果（大量刪除時用） |

---

### `remove_orphan_files`

```sql
CALL retail.system.remove_orphan_files(
  table      => 'retail.inventory.orders',
  older_than => TIMESTAMP '2025-01-01 00:00:00'
)
```

掃描表的 storage location，找出**不被任何現存 snapshot 參照**的檔案並刪除。這類孤立檔案可能來自失敗的寫入、手動操作或其他異常情況。

!!! warning "使用 `dry_run` 先確認"
    第一次執行時，建議加上 `dry_run => true` 先看清單，確認沒有誤刪的風險再正式執行。

**可用環境變數：**

| 環境變數 | 說明 |
|---|---|
| `GLAC_REMOVE_ORPHAN_FILES__TABLE` | 目標表 |
| `GLAC_REMOVE_ORPHAN_FILES__OLDER_THAN` | 只刪除比這個時間更舊的孤立檔案，預設 3 天前 |
| `GLAC_REMOVE_ORPHAN_FILES__LOCATION` | 覆蓋掃描路徑（選填） |
| `GLAC_REMOVE_ORPHAN_FILES__DRY_RUN` | `true` 時只列出，不刪除 |
| `GLAC_REMOVE_ORPHAN_FILES__MAX_CONCURRENT_DELETES` | 並行刪除數 |

---

### `rewrite_manifests`

```sql
CALL retail.system.rewrite_manifests(
  table      => 'retail.inventory.orders',
  use_caching => true
)
```

Iceberg 的 metadata 層由 manifest files 組成，記錄每個資料檔的 statistics 和 partition 資訊。大量小寫入之後，manifest 也會碎片化。`rewrite_manifests` 把多個 manifest 合併成更少、更大的檔案，加快 query planning 速度（Spark 掃描 metadata 的時間減少）。

**可用環境變數：**

| 環境變數 | 說明 |
|---|---|
| `GLAC_REWRITE_MANIFESTS__TABLE` | 目標表 |
| `GLAC_REWRITE_MANIFESTS__USE_CACHING` | 使用 Spark cache 加速，預設 `true` |
| `GLAC_REWRITE_MANIFESTS__SPEC_ID` | 指定 partition spec ID（選填） |

---

## 這個專案怎麼跑維護作業

### 架構概覽

維護作業是一個跑在 Kubernetes 上的 **PySpark job**，透過 Spark Operator 的 `SparkApplication` CRD 提交。

```
環境變數
  ↓
JobSettings (pydantic-settings)
  ↓
IcebergCallBuilder.build_sql()
  ↓
CALL SQL
  ↓
SparkSession.sql(sql)
  ↓
Iceberg Spark Extensions 執行
```

程式碼位置：`src/table-maintenance/runtime/spark/`

- `main.py` — 入口點，讀取設定、建立 SparkSession、執行 SQL
- `configs/job_settings.py` — 頂層設定（`GLAC_JOB_TYPE`、`GLAC_CATALOG`）
- `configs/jobs/rewrite_data_files.py` — `rewrite_data_files` 的完整參數定義
- `sql_builder.py` — `IcebergCallBuilder`，把設定轉成 `CALL` SQL

### 關鍵前提條件

!!! important "Iceberg Spark Runtime JAR"
    Spark 本身不內建 Iceberg 支援。`SparkApplication` 必須在 `deps.jars` 中指定 Iceberg Spark runtime JAR，否則 `CALL` 語法和 Iceberg Spark extensions 都無法使用。

    本專案使用：
    ```
    iceberg-spark-runtime-4.0_2.13-1.10.1.jar
    iceberg-aws-bundle-1.10.1.jar
    ```
    兩個 JAR 都從 Maven Central 在 job 啟動時下載。

!!! important "Spark Extensions 設定"
    `SparkApplication` 的 `sparkConf` 必須啟用 Iceberg extensions：
    ```yaml
    spark.sql.extensions: "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
    ```
    沒有這行，`CALL` 語法會報 `ParseException`。

!!! important "AWS/MinIO 憑證"
    `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_REGION` 必須同時設定在 **driver** 和 **executor** 的 env 區塊。Executor 直接讀取 S3/MinIO，缺少憑證會在資料讀寫時失敗，而不是啟動時失敗。

### 環境變數設定

所有設定都透過環境變數傳入，前綴為 `GLAC_`，巢狀參數用 `__` 分隔。

**最小必要設定（`rewrite_data_files`）：**

```bash
GLAC_JOB_TYPE=rewrite_data_files
GLAC_CATALOG=retail
GLAC_REWRITE_DATA_FILES__TABLE=inventory.orders
```

加上這組設定，job 會生成並執行：

```sql
CALL retail.system.rewrite_data_files(
  table => 'retail.inventory.orders',
  strategy => 'binpack'
)
```

**加上 `rewrite-all` 選項（對應 `sparkapplication-rewrite-data-files.yaml` 的設定）：**

```bash
GLAC_JOB_TYPE=rewrite_data_files
GLAC_CATALOG=retail
GLAC_REWRITE_DATA_FILES__TABLE=inventory.orders
GLAC_REWRITE_DATA_FILES__REWRITE_ALL=true
```

生成的 SQL：

```sql
CALL retail.system.rewrite_data_files(
  table => 'retail.inventory.orders',
  strategy => 'binpack',
  options => map('rewrite-all', 'true')
)
```

---

## 提交與監控作業

### 完整流程

```bash
# 1. 建立 Docker image 並載入 Minikube
./25-table-maintenance/build.sh

# 2. 提交 SparkApplication
./25-table-maintenance/install.sh

# 3. 查看 driver log（即時串流）
kubectl logs -n default \
  -l spark-role=driver,spark-app-name=table-maintenance-rewrite-data-files \
  -f
```

### 確認 job 狀態

```bash
# 查看 SparkApplication 的狀態
kubectl get sparkapplication table-maintenance-rewrite-data-files -n default

# 查看所有相關 pods
kubectl get pods -n default -l spark-app-name=table-maintenance-rewrite-data-files
```

`SparkApplication` 的 `state` 欄位會顯示 `RUNNING`、`COMPLETED` 或 `FAILED`。

---

## 實際執行結果

以下是在 `retail.inventory.orders` 表上執行 `rewrite_data_files` 的真實結果：

```
CALL retail.system.rewrite_data_files(
  table => 'retail.inventory.orders',
  strategy => 'binpack',
  options => map('rewrite-all', 'true')
)

rewritten_data_files_count: 4
added_data_files_count:     1
rewritten_bytes_count:      19479
```

| 指標 | 數值 |
|---|---|
| 輸入檔案數 | 4 個小檔案 |
| 輸出檔案數 | 1 個合併檔案 |
| 重寫資料量 | 19,479 bytes（約 19 KB） |
| 新檔案大小 | 8,636 bytes（壓縮後更小） |
| 執行時間 | 約 22 秒 |

!!! note "為什麼輸出比輸入小？"
    輸出檔案（8,636 bytes）比輸入總量（19,479 bytes）小，是因為 `rewrite_data_files` 在合併時會重新編碼 Parquet，加上更好的 column statistics 和 dictionary encoding，使壓縮率提升。這是正常現象。

---

## 快速參考：環境變數總覽

### 共用設定

| 環境變數 | 必填 | 說明 |
|---|---|---|
| `GLAC_JOB_TYPE` | 是 | `rewrite_data_files` \| `expire_snapshots` \| `remove_orphan_files` \| `rewrite_manifests` |
| `GLAC_CATALOG` | 否 | Iceberg catalog 名稱，預設 `spark_catalog` |

### `rewrite_data_files` 參數

| 環境變數 | 必填 | 預設值 | 說明 |
|---|---|---|---|
| `GLAC_REWRITE_DATA_FILES__TABLE` | 是 | — | `<namespace>.<table>` |
| `GLAC_REWRITE_DATA_FILES__STRATEGY` | 否 | `binpack` | `binpack` \| `sort` \| `zorder` |
| `GLAC_REWRITE_DATA_FILES__SORT_ORDER` | 否 | — | 排序表達式（sort/zorder 用） |
| `GLAC_REWRITE_DATA_FILES__WHERE` | 否 | — | 只 compact 符合條件的 partitions |
| `GLAC_REWRITE_DATA_FILES__TARGET_FILE_SIZE_BYTES` | 否 | 536870912 | 目標檔案大小（bytes） |
| `GLAC_REWRITE_DATA_FILES__MIN_FILE_SIZE_BYTES` | 否 | 75% of target | 小於此值才納入 compaction |
| `GLAC_REWRITE_DATA_FILES__MAX_FILE_SIZE_BYTES` | 否 | 180% of target | 大於此值不重寫 |
| `GLAC_REWRITE_DATA_FILES__MIN_INPUT_FILES` | 否 | 5 | 觸發重寫的最小檔案數 |
| `GLAC_REWRITE_DATA_FILES__REWRITE_ALL` | 否 | false | 強制重寫所有檔案 |
| `GLAC_REWRITE_DATA_FILES__MAX_CONCURRENT_FILE_GROUP_REWRITES` | 否 | 1 | 並行 file group 數 |
| `GLAC_REWRITE_DATA_FILES__PARTIAL_PROGRESS_ENABLED` | 否 | false | 啟用批次提交 |
| `GLAC_REWRITE_DATA_FILES__PARTIAL_PROGRESS_MAX_COMMITS` | 否 | 10 | 最大批次提交數 |
