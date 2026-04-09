# Troubleshooting: Iceberg Spark Runtime 版本相容性

> **適合讀者**：第一次設定 Iceberg + Spark 4.0 的開發者。這篇記錄一個很常見、但錯誤訊息不直觀的坑：**指定了根本不存在的 JAR 版本**。

---

## 症狀 Symptom

你提交了一個 `SparkApplication`，它在幾秒內就失敗，driver pod 的日誌裡出現這樣的錯誤：

```
java.io.FileNotFoundException:
  https://repo1.maven.org/maven2/org/apache/iceberg/
  iceberg-spark-runtime-4.0_2.13/1.8.1/
  iceberg-spark-runtime-4.0_2.13-1.8.1.jar
```

緊接著：

```
at org.apache.spark.util.DependencyUtils.downloadFile(DependencyUtils.scala:...)
at org.apache.spark.deploy.SparkSubmit.prepareSubmitEnvironment(SparkSubmit.scala:...)
```

Job 完全沒有跑任何 Iceberg 程式，就直接掛了。

---

## 根本原因

### Iceberg 的 JAR 命名規則

Iceberg 為不同版本的 Spark 和 Scala 分別發布獨立的 JAR artifact。命名格式是：

```
iceberg-spark-runtime-{spark版本}_{scala版本}-{iceberg版本}.jar
```

例如：
- Spark 3.5 + Scala 2.12 → `iceberg-spark-runtime-3.5_2.12-1.8.1.jar`  ✅ 存在
- Spark 4.0 + Scala 2.13 → `iceberg-spark-runtime-4.0_2.13-1.8.1.jar`  ❌ **不存在**

### Iceberg 1.8.x 沒有支援 Spark 4.0

Apache Iceberg 對 Spark 4.0 的支援是在 **Iceberg 1.10.0** 才加入的。

| Iceberg 版本 | 支援 Spark 4.0？ |
|---|---|
| 1.7.x | ❌ |
| 1.8.x | ❌ |
| 1.9.x | ❌ |
| **1.10.0** | ✅ |
| **1.10.1** | ✅（建議使用） |

在 Maven Central 上可以確認：搜尋 `iceberg-spark-runtime-4.0_2.13`，你只會找到 `1.10.0` 和 `1.10.1`，1.8.x 根本沒有這個 artifact。

### 為什麼這個錯誤不直觀？

Spark 在啟動時會下載 `deps.jars` 裡列出的所有 JAR。如果 JAR URL 404（檔案不存在），Spark 拋出的是 `FileNotFoundException`，而不是「版本不相容」之類的提示訊息。你看到 `FileNotFoundException` 第一反應可能是「網路問題」或「Maven 服務不穩」，但實際上是座標（group ID + artifact ID + version）根本不存在。

---

## 修復方法

將 `SparkApplication` manifest 中的 Iceberg JAR 版本改為 `1.10.1`：

```yaml
spec:
  deps:
    jars:
      # iceberg-spark-runtime：支援 Spark 4.0 的最低版本是 1.10.0
      - https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.13/1.10.1/iceberg-spark-runtime-4.0_2.13-1.10.1.jar
      # AWS bundle 版本必須與 runtime 一致
      - https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar
```

!!! warning "兩個 JAR 的版本要一致"

    `iceberg-spark-runtime` 和 `iceberg-aws-bundle` 必須使用**同一個 Iceberg 版本**。混用版本（例如 runtime 用 1.10.1，aws-bundle 用 1.8.1）可能導致執行時類別衝突（`NoClassDefFoundError` 或 `ClassNotFoundException`），問題更難追蹤。

---

## 驗證修復

提交修復後的 manifest 並觀察 driver pod 日誌：

```bash
kubectl apply -f 25-table-maintenance/sparkapplication-rewrite-data-files.yaml

kubectl logs -n default \
  -l spark-role=driver \
  -f
```

如果 JAR 成功下載，你會看到類似這樣的日誌：

```
INFO DependencyUtils: Fetching iceberg-spark-runtime-4.0_2.13-1.10.1.jar
  from https://repo1.maven.org/...
INFO DependencyUtils: Fetching iceberg-aws-bundle-1.10.1.jar
  from https://repo1.maven.org/...
```

緊接著 Spark context 正常初始化，沒有 `FileNotFoundException`。

---

## 延伸說明：為什麼用 HTTPS URL 而非 Docker image 內建 JAR？

本專案選擇在 `deps.jars` 裡放 HTTPS URL，由 Spark Operator 在 job 啟動時從 Maven Central 下載 JAR，而不是把 JAR 直接打包進 Docker image。

這個設計的好處是：

- **Image 體積小**：Iceberg runtime JAR 約 50MB，AWS bundle 約 100MB，不打包就能省下 150MB+。
- **版本更新方便**：換版本只需改 URL，不需要重新 build image。

代價是：Spark driver 啟動時需要網路連線到 Maven Central。在本地 Minikube 環境下，只要 driver pod 有外網存取能力，就沒問題。

!!! tip "JAR 下載失敗的兩種原因"

    1. **座標不存在**（本文描述的情況）：`FileNotFoundException`，HTTP 404。
    2. **網路不通**：連線 timeout 或 connection refused。這時候應檢查 Minikube 的網路設定，而不是 JAR 版本。

---

## 快速總結

| 狀況 | 說明 |
|------|------|
| 錯誤訊息 | `FileNotFoundException: ...iceberg-spark-runtime-4.0_2.13-1.8.1.jar` |
| 根本原因 | Iceberg 1.8.x 沒有 Spark 4.0 的 artifact |
| 修復方式 | 改用 Iceberg `1.10.1`（runtime + aws-bundle 都要改） |
| 最低相容版本 | Iceberg 1.10.0 是第一個支援 Spark 4.0 的版本 |
