# Troubleshooting: Minikube Worker Node NotReady

在 local Kubernetes 開發環境中，最讓人措手不及的故障之一就是某個 worker node 突然進入 `NotReady` 狀態。這篇文章記錄了完整的連鎖反應、診斷步驟，以及如何從輕量修復到核武選項（full restart）分級處理。

---

## 症狀 Symptom

你執行 `kubectl get nodes` 時，看到其中一個 node 的 `STATUS` 不是 `Ready`：

```bash
kubectl get nodes -o wide
```

```
NAME                 STATUS     ROLES           AGE   VERSION
lakehouse-demo       Ready      control-plane   3d    v1.31.0
lakehouse-demo-m02   NotReady   <none>          3d    v1.31.0
```

`lakehouse-demo-m02` 出問題了。它變成 `NotReady` 代表這個 node 上的 kubelet 已經無法正常向 API server 回報心跳（heartbeat）。

---

## 連鎖反應 What Happens Downstream

Node 進入 `NotReady` 之後，問題不會就停在那裡。Kubernetes 的設計是讓系統自動恢復，但在 local Minikube 環境下，這些自動恢復機制反而會引發一連串的放大效應。

### 第一層：Pods 卡在 Terminating

Kubernetes controller 偵測到 node 失聯後，會嘗試把原本在那個 node 上跑的 pods 驅逐（evict）。它會發出刪除指令，pods 的狀態於是變成 `Terminating`。

問題在於：pod 的 graceful termination 需要 node 上的 kubelet 來執行（發 SIGTERM、等待、清理）。Node 既然已經 `NotReady`，kubelet 不回應，這些 pods 就永遠等在 `Terminating` 狀態，哪裡也去不了。

```bash
kubectl get pods -A | grep -E "Terminating|Error|CrashLoop"
```

```
spark            spark-operator-7d9f6b-xxxxx   0/1   Terminating   0   10m
kafka            kafka-broker-0                0/1   Terminating   0   10m
kafka            kafka-broker-1                0/1   Terminating   0   10m
trino            trino-coordinator-xxxx        0/1   Terminating   0   12m
```

!!! warning "Terminating 不等於已刪除"

    很多人第一次看到 `Terminating` 以為 pod 快要消失了，只要等一下就好。但如果 node 是 `NotReady`，這些 pod **永遠不會自動消失**。它們會一直掛在那裡，佔用 Kubernetes 的資源記錄，直到有人手動介入。

### 第二層：API Server 被拖垮

每個卡住的 `Terminating` pod 背後都有各種 controller 不斷嘗試協調（reconcile）它的狀態。當這些 pod 越堆越多，reconcile 請求也越來越多，最終造成 Kubernetes API server 的 handler 積壓。你開始看到像這樣的超時訊息：

```
context deadline exceeded (or handler timeout)
```

這時候連 `kubectl get pods` 都可能要等很久甚至 timeout，因為 API server 已經在處理大量積壓請求了。

### 第三層：Operator 開始 Crash

以 Spark operator 為例，它需要定期向 API server 更新 leader election 的 lease。如果 API server 太慢回應，Spark operator 的 leader election `renewDeadline` 就會超時：

```
failed to renew leader election record: ...
renewDeadline exceeded ...
leaderelection.go:330] failed to acquire lease spark/spark-operator-lock
```

Operator crash 之後，所有 SparkApplication 都暫時失去管理，整個 Spark 工作流程中斷。同樣的情況也可能發生在 Strimzi（Kafka operator）或其他任何依賴 leader election 的 controller 上。

!!! info "雪球效應"

    這整個過程像是雪球效應：

    1 個 node `NotReady`
    → N 個 pods 卡在 `Terminating`
    → API server handler 積壓
    → 所有 controllers 的 reconcile 變慢
    → Leader election 超時
    → Operators crash
    → 更多 pods 進入異常狀態

    在 local 環境下，資源本來就有限，這個放大效應特別明顯。

---

## 診斷步驟 Diagnosis

按照以下順序診斷，從全局到細節。

### Step 1：確認 Node 狀態

```bash
kubectl get nodes -o wide
```

看 `STATUS` 欄位。`Ready` 以外的狀態（`NotReady`、`Unknown`）都代表問題。`-o wide` 可以同時看到每個 node 的 IP 和目前跑的 Kubernetes 版本。

### Step 2：找出異常 Pods

```bash
kubectl get pods -A | grep -E "Terminating|Error|CrashLoop"
```

如果輸出很長，說明問題已經擴散。留意 `Terminating` pod 的 `AGE`——如果已經卡了超過幾分鐘，代表它確實是 stuck pod，不是正在正常關機。

### Step 3：查看 Node 的事件與狀態詳情

```bash
kubectl describe node lakehouse-demo-m02
```

重點看 `Conditions` 區塊，以及最底下的 `Events`。常見的訊號包括：

- `KubeletNotReady`：kubelet 無法正常運行
- `NodeNotSchedulable`：node 被 taint 為不可排程
- `DiskPressure` / `MemoryPressure`：資源耗盡

### Step 4：查看 Operator Logs

如果懷疑 Spark operator 或其他 operator 已經 crash，查看它的 log：

```bash
kubectl logs -l app.kubernetes.io/name=spark-operator -n spark --tail=50
```

找 `renewDeadline exceeded`、`failed to acquire lease`、`context deadline exceeded` 這類關鍵字，確認是否是 API server 過載造成的。

---

## 修復方案 Fix

### 方案一：逐一強制刪除 Stuck Pods

最精準的方式是針對每個 stuck pod 執行強制刪除：

```bash
kubectl delete pod <pod-name> -n <namespace> --force --grace-period=0
```

`--force --grace-period=0` 告訴 Kubernetes：跳過 graceful termination，直接從 etcd 裡把這個 pod 的記錄移除，不等 kubelet 確認。

!!! warning "強制刪除的代價"

    `--force --grace-period=0` 繞過了 pod 的正常關機程序。如果應用程式有 `preStop` hook 或需要優雅關機（例如 Kafka broker 的 leader 切換），強制刪除可能造成短暫的資料不一致。

    在 local 開發環境下，這通常可以接受。在生產環境要謹慎評估。

### 方案二：批次強制刪除所有 Stuck Pods

如果 stuck pods 數量很多，一個一個刪太費時。可以用這個一行指令批次處理：

```bash
kubectl get pods -A | grep Terminating | awk '{print "kubectl delete pod " $2 " -n " $1 " --force --grace-period=0"}' | bash
```

!!! info "這行指令的邏輯"

    1. `kubectl get pods -A`：列出所有 namespace 的 pods
    2. `grep Terminating`：只留下卡住的那些
    3. `awk '{print "kubectl delete pod " $2 " -n " $1 " --force --grace-period=0"}'`：把每一行轉成對應的 delete 指令（`$1` 是 namespace，`$2` 是 pod name）
    4. `| bash`：直接執行產生出來的指令

    執行前可以先去掉最後的 `| bash`，先看看會產生哪些指令，確認後再加回去執行。

批次刪除完成後，重新確認：

```bash
kubectl get pods -A | grep -E "Terminating|Error|CrashLoop"
```

如果輸出清空，API server 的壓力會隨之下降，operators 通常也會在幾分鐘內自動恢復 leader election。

---

## 核武選項：完整重啟 Minikube

如果強制刪除 pods 之後問題仍然持續，或是 node 依然 `NotReady`，最乾淨的解法是把整個 Minikube profile 重啟。

```bash
minikube stop -p lakehouse-demo
```

```bash
minikube start -p lakehouse-demo
```

!!! tip "重啟會清除所有 transient 狀態"

    Minikube 重啟相當於把整台虛擬機器重新開機。Kubernetes 的所有 transient 狀態（stuck pods、卡住的 controller、leader election 鎖）都會被清除。重啟後，Kubernetes 從乾淨的狀態啟動，所有 namespace 裡的 Deployments 和 StatefulSets 會由各自的 controller 重新調度。

    這是最確保狀態一致的方式，代價是所有服務都需要重新等待啟動。

### 重啟後的驗證

重啟後，先確認所有 nodes 都回到 `Ready`：

```bash
kubectl get nodes -o wide
```

再確認核心 pods 都是 `Running`：

```bash
kubectl get pods -A
```

!!! warning "重啟後記得驗證 Stateful 服務"

    重啟後，特別需要注意兩類有 stateful 性質的服務：

    **1. Polaris（in-memory persistence）**

    Polaris 預設使用 in-memory persistence。Pod 重啟後，所有 catalog metadata（catalog 定義、namespaces、tables）都會消失。需要重新執行 Polaris 的初始化設定腳本，建立 catalog 和授權規則。

    ```bash
    kubectl get pods -n polaris
    # 確認 polaris pod 是 Running 後，重新執行初始化
    bash 21-polaris/setup.sh
    ```

    **2. MinIO（hostPath storage）**

    MinIO 使用 `hostPath` 把資料存在 Minikube node 的本機路徑上。只要 node 的 volume 沒有被清除，資料通常在重啟後還在。但仍建議確認一下：

    ```bash
    kubectl get pods -n minio
    kubectl exec -n minio deploy/minio -- mc ls local/
    ```

    如果 bucket 或物件不見了，表示 hostPath 被清除了，需要重新執行 MinIO 的初始化流程。

---

## 為什麼 Minikube Node 會進入 NotReady？

Node 進入 `NotReady` 的根本原因通常是 kubelet 無法正常運行。在 Minikube local 環境下，常見的觸發因素有以下幾類：

### 主機資源耗盡（最常見）

Minikube 在 Docker 或虛擬機器裡跑 Kubernetes，它可用的 RAM 和 CPU 受到 Minikube profile 設定的限制。當你同時跑 Kafka cluster、Spark operator、Trino、MinIO、Polaris，很容易把 node 的記憶體壓力推到上限。

一旦 node 發生 OOM（Out of Memory），kubelet 自己也可能被 kernel 的 OOM killer 終止。kubelet 一死，API server 就收不到心跳，node 狀態切換到 `NotReady`。

```bash
# 查看 node 的資源用量（需要 metrics-server）
kubectl top nodes
kubectl top pods -A --sort-by=memory
```

### Kubelet Crash 或 Hang

有時是 kubelet 本身遇到 bug 或無法處理的邊際情況而 crash。Minikube 通常會自動重啟 kubelet，但如果問題持續，kubelet 就無法維持 `Ready` 狀態。

### Docker Daemon 問題

如果 Minikube 用 Docker driver 跑（這是 Mac 上最常見的設定），Docker Desktop 本身的問題也會影響 node 的穩定性。Docker daemon 卡住或重啟都可能導致 kubelet 失去與 container runtime 的連線。

!!! tip "預防 Node 不穩定的幾個做法"

    - **給 Minikube 足夠的資源**：建立 profile 時用 `--cpus` 和 `--memory` 給充裕的配額，例如 `--cpus=6 --memory=12288`。
    - **不要跑太多服務**：在 local 環境下，按照 wave 分階段部署，不要把所有服務一次全開。
    - **定期清理**：用 `kubectl delete` 清掉不再需要的 pods 和 jobs，避免資源積壓。
    - **監控資源**：如果有安裝 metrics-server，定期用 `kubectl top nodes` 觀察用量趨勢。

---

## 總結 Summary

| 情境 | 建議動作 |
|------|---------|
| 少數 pods 卡在 `Terminating` | 逐一 `kubectl delete pod --force --grace-period=0` |
| 大量 pods 卡住，API server 變慢 | 批次刪除 + 等 operators 自動恢復 |
| Node 一直無法回到 `Ready` | `minikube stop / start -p lakehouse-demo` |
| 重啟後服務異常 | 重新初始化 Polaris catalog；驗證 MinIO 資料完整性 |

在 local 開發環境下，Minikube node 的不穩定是正常現象，不需要太緊張。掌握這套診斷和修復流程，大多數狀況都可以在幾分鐘內恢復。
