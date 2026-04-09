# 排查 Spark Operator 的 Leader Election 崩潰循環

> **適合讀者**：不熟悉 Kubernetes Operator 機制的團隊成員。這篇文章從基本概念出發，帶你一步步理解為什麼 Spark Operator 會進入崩潰重啟循環，以及如何診斷和修復。

---

## 1. 什麼是 Leader Election？

在 Kubernetes 中，很多元件（包含 Spark Operator）會以多個副本（replica）的形式運行，以確保高可用性（High Availability）。但如果多個副本同時發出指令，就可能造成衝突。**Leader Election（領導者選舉）** 機制就是為了解決這個問題。

### 運作原理

Leader Election 使用 Kubernetes 的 `Lease` 物件，它存放在 `coordination.k8s.io` API group 下。你可以把 `Lease` 想像成一把鑰匙——誰持有這把鑰匙，誰就是當前的 Leader，只有 Leader 才能實際執行控制邏輯。

```
┌─────────────────────────────────────────────────┐
│          coordination.k8s.io/Lease               │
│                                                   │
│  holderIdentity:  spark-operator-pod-abc123       │
│  acquireTime:     2026-04-03T08:00:00Z            │
│  renewTime:       2026-04-03T08:00:08Z  ← 每隔幾秒更新 │
│  leaseDurationSeconds: 15                         │
└─────────────────────────────────────────────────┘
```

### 三個關鍵參數

| 參數 | 預設值 | 意義 |
|------|--------|------|
| `leaseDuration` | 15s | Lease 的有效期限。超過此時間未更新，其他副本可搶奪領導權 |
| `renewDeadline` | **10s** | Leader 必須在這段時間內完成續約，否則主動放棄領導權 |
| `retryPeriod` | **2s** | 嘗試取得或更新 Lease 的間隔 |

!!! info "簡單比喻"

    `renewDeadline = 10s` 意思是：Leader 有 10 秒的時間向 API Server 說「我還在！」。
    如果它在 10 秒內無法成功打 API，就會自行宣布放棄領導權並結束程式。

---

## 2. 崩潰循環的症狀

當 Spark Operator 進入崩潰重啟循環時，你會看到以下現象：

### 2.1 Pod 不斷重啟

```bash
kubectl get pods -n spark-operator
```

!!! failure "異常輸出範例"

    ```
    NAME                              READY   STATUS             RESTARTS   AGE
    spark-operator-7d9f8b6c5-xk2p9   0/1     CrashLoopBackOff   5          8m
    ```

    `RESTARTS: 5` 表示這個 Pod 在短時間內已重啟了 5 次，這是最明顯的警示訊號。

### 2.2 Pod 日誌出現 Leader Election 失敗

```bash
kubectl logs -n spark-operator deployment/spark-operator --tail=50
```

!!! failure "典型錯誤日誌"

    ```
    E0403 08:12:34.567890       1 leaderelection.go:330] error retrieving resource lock
    spark-operator/spark-operator: failed to renew lease
    spark-operator/spark-operator: context deadline exceeded

    I0403 08:12:34.567891       1 leaderelection.go:285] failed to renew lease
    spark-operator/spark-operator: context deadline exceeded

    I0403 08:12:34.567892       1 leaderelection.go:296] leader election lost
    ```

    關鍵字：
    - `failed to renew lease` — 無法更新 Lease 物件
    - `context deadline exceeded` — HTTP 請求超時
    - `leader election lost` — 放棄領導權，程式即將退出

---

## 3. 為什麼會發生？API Server 過載的連鎖反應

### 3.1 根本原因：Kubernetes API Server 過載

Spark Operator 使用 Kubernetes HTTP client 向 API Server 發送請求。**這個 client 預設有 5 秒的 timeout**。

當 Kubernetes API Server 處於過載狀態（例如：某個 Node 變成 `NotReady`，造成大量 Pod 卡在 `Terminating` 狀態無法刪除，進而引發 handler timeout 堆積），每一次 API 請求可能都要等到超時才回應。

### 3.2 數學很殘酷

```
renewDeadline = 10 秒
每次 HTTP 請求 timeout = 5 秒

失敗的第 1 次請求：等了 5 秒，超時
失敗的第 2 次請求：又等了 5 秒，超時
                   ─────────────────
                   總計：10 秒 = renewDeadline 到期！
```

!!! warning "致命的巧合"

    兩次連續的 5 秒 HTTP timeout 恰好等於 `renewDeadline` 的 10 秒上限。
    Spark Operator 隨即宣布 `leader election lost` 並主動退出——這是設計上的正確行為，但在 API Server 過載時卻成為觸發崩潰循環的導火線。

### 3.3 完整的連鎖反應

```
Node 變成 NotReady
        │
        ▼
Pod 卡在 Terminating 狀態（無法被正常刪除）
        │
        ▼
Kubernetes API Server 被大量 garbage collection 請求擠爆
        │
        ▼
API Server 回應極度緩慢，出現 handler timeout
        │
        ▼
Spark Operator 發出 Lease 續約請求 → 等 5 秒 → 超時
Spark Operator 再次嘗試 → 等 5 秒 → 再次超時
        │
        ▼
renewDeadline (10s) 耗盡 → leader election lost → 程式退出
        │
        ▼
Kubernetes 偵測到 Pod 異常退出 → 重啟 Pod
        │
        ▼
新 Pod 啟動，嘗試競選 Leader → API Server 依然過載 → 再次失敗
        │
        ▼
💥 CrashLoopBackOff
```

!!! danger "關鍵觀察"

    Spark Operator 本身並沒有 bug。它是在做正確的事——當它無法維持 Leader 身份時，就乾淨地退出，讓其他副本有機會接管。問題在於 API Server 的過載讓它永遠無法完成續約，形成一個永無止盡的循環。

---

## 4. 診斷步驟

依序執行以下指令，從症狀追溯到根本原因。

### 步驟 1：確認 Operator Pod 是否不斷重啟

```bash
kubectl get pods -n spark-operator
```

注意 `RESTARTS` 欄位的數值。若在幾分鐘內就累積到 3 次以上，幾乎可以確定是崩潰循環。

### 步驟 2：查看 Operator 日誌

```bash
kubectl logs -n spark-operator deployment/spark-operator --tail=50
```

搜尋以下關鍵字：

- `failed to renew lease`
- `context deadline exceeded`
- `leader election lost`

如果三者都出現，Leader Election 失敗就是直接原因。

### 步驟 3：確認 API Server 的健康狀態

```bash
kubectl get --raw /healthz
```

!!! success "健康的 API Server"

    ```
    ok
    ```

!!! failure "過載的 API Server"

    回應可能非常慢（數秒後才回應），或是直接超時。若這個指令本身就要等很久，API Server 的過載幾乎可以確定。

### 步驟 4：尋找 handler timeout 的蛛絲馬跡

查看叢集中其他 Pod 的日誌，尋找 `handler timeout` 或 `etcd` 相關的錯誤：

```bash
# 查看系統元件命名空間的最近事件
kubectl get events -n kube-system --sort-by='.lastTimestamp' | tail -20

# 查看是否有卡住的 Terminating pods
kubectl get pods --all-namespaces | grep Terminating
```

如果看到大量 `Terminating` 的 Pod，這幾乎就是 API Server 過載的根源。

---

## 5. 修復方法

### 5.1 清除根本原因：讓 API Server 恢復健康

**方法 A：強制刪除卡住的 Pod**

```bash
# 先找出所有卡在 Terminating 的 Pod
kubectl get pods --all-namespaces | grep Terminating

# 強制刪除（加上 --grace-period=0 --force）
kubectl delete pod <pod-name> -n <namespace> --grace-period=0 --force
```

!!! warning "謹慎使用 --force"

    `--force` 會繞過 graceful shutdown 流程，直接從 etcd 中移除 Pod 的記錄。
    通常只用在 Pod 因為 Node 異常而真的無法正常終止的情況。

**方法 B：重啟 Minikube（本地開發環境）**

如果你在使用 Minikube 且問題難以追蹤，重啟 Minikube 是最快的方式：

```bash
minikube stop
minikube start
```

!!! info "重啟後的預期行為"

    API Server 恢復健康後，Spark Operator 重啟時就能成功完成 Lease 續約，`CrashLoopBackOff` 會自動消失，Pod 進入 `Running` 狀態。

### 5.2 確認 Spark Operator 已恢復正常

```bash
kubectl get pods -n spark-operator
```

!!! success "恢復正常的狀態"

    ```
    NAME                              READY   STATUS    RESTARTS   AGE
    spark-operator-7d9f8b6c5-xk2p9   1/1     Running   0          2m
    ```

    `STATUS: Running` 且 `RESTARTS: 0`（或不再增加）就表示問題已解決。

---

## 6. Helm Rollback 的陷阱

在問題發生當下，你可能會想透過 `helm upgrade` 來調整 Leader Election 的 timeout 參數（例如拉長 `renewDeadline`）。這個想法合理，但有一個隱藏的風險。

### 問題所在

```bash
# 看似合理的嘗試：upgrade 來調整參數
helm upgrade spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --set leaderElection.renewDeadline=30s
```

`helm upgrade` 會從 Helm repository 下載最新版的 chart。**如果最新版 chart 指定了一個在你的環境中拉不到的新 image tag**（例如私有 registry 無法存取，或是網路不穩），你的 Spark Operator 會從「崩潰循環」直接變成「ImagePullBackOff」——反而更慘。

!!! danger "常見陷阱"

    在叢集不穩定的狀態下執行 `helm upgrade`，可能因為 image pull 失敗而讓問題從「可自動恢復」變成「需要手動介入」。

### 安全的退路：helm rollback

如果你已經執行了 `helm upgrade` 且遇到 image pull 問題，用 `helm rollback` 回到上一個已知的好版本：

```bash
# 查看 Helm release 的歷史記錄
helm history spark-operator -n spark-operator
```

!!! info "歷史記錄範例"

    ```
    REVISION  UPDATED                   STATUS     CHART                    APP VERSION  DESCRIPTION
    1         Thu Apr  3 08:00:00 2026  superseded spark-operator-1.3.2     v1beta2      Install complete
    2         Thu Apr  3 08:15:00 2026  failed     spark-operator-1.4.0     v1beta2      Upgrade failed
    ```

```bash
# 回滾到上一個版本（revision 1）
helm rollback spark-operator 1 -n spark-operator
```

```bash
# 確認回滾成功
helm status spark-operator -n spark-operator
kubectl get pods -n spark-operator
```

!!! tip "最佳實踐"

    在叢集出現問題時，**優先修復底層原因**（清除卡住的 Pod、恢復 API Server 健康），而不是急著調整 Operator 的配置。配置調整應該在環境穩定後，經過測試再套用。

---

## 7. 總結

| 現象 | 意義 |
|------|------|
| `RESTARTS` 持續增加 | Pod 在異常退出後被 Kubernetes 自動重啟 |
| `context deadline exceeded` | HTTP 請求在 5 秒內未收到回應 |
| `leader election lost` | `renewDeadline` 耗盡，Operator 主動退出 |
| `CrashLoopBackOff` | 重啟次數過多，Kubernetes 開始延長重啟間隔 |

**診斷流程一覽：**

```
kubectl get pods -n spark-operator    ← 確認重啟次數
        │
        ▼
kubectl logs ... --tail=50            ← 確認 leader election lost
        │
        ▼
kubectl get --raw /healthz            ← 確認 API Server 是否過載
        │
        ▼
kubectl get pods --all-namespaces | grep Terminating  ← 找根本原因
        │
        ▼
kubectl delete pod ... --grace-period=0 --force       ← 清除卡住的 Pod
```

!!! success "關鍵結論"

    Spark Operator 的崩潰循環通常不是 Operator 本身的問題，而是 **Kubernetes API Server 過載** 的症狀。修復重點在於恢復 API Server 的健康，而非調整 Operator 的配置。
