# MinIO Data Recovery: hostPath Volume 與節點重排程問題

*Troubleshooting Guide for Dev Cluster Data Disappearance*

---

## 背景：什麼是 hostPath？

When you deploy MinIO on a Kubernetes cluster, the data has to live *somewhere* on disk. In development clusters like ours, the simplest option is a **hostPath volume** — a Kubernetes volume type that mounts a directory directly from the host node's filesystem into the pod.

用人話說：就是 Kubernetes 把某個節點上的本機資料夾「借」給 Pod 使用，讓 Pod 裡的程式可以讀寫那個資料夾，就好像那個資料夾是 Pod 自己的本地磁碟一樣。

In this project, MinIO stores all of its data at this path on the node:

```
/home/docker/data/minio
```

這個路徑存放了所有 S3 bucket、Parquet 檔案、以及 Iceberg 的 metadata。

!!! warning "Production 環境請勿使用 hostPath"
    hostPath 只適合開發環境的快速驗證。正式環境應改用 PersistentVolume 搭配適當的 StorageClass（例如 Longhorn、Rook/Ceph），或直接使用雲端的物件儲存服務（AWS S3、GCS 等）。原因正是下面要說明的問題。

---

## 問題所在：Pod 重啟後資料「消失」了

Here is where things get tricky. A hostPath volume is tied to the **specific node** the pod is running on. If the pod gets rescheduled to a **different node**, the new node has an empty directory at `/home/docker/data/minio` — and your data appears to be gone.

The data is not actually lost. It is still sitting on the original node's filesystem. But the pod is no longer running there, so it cannot see any of it.

這就是 hostPath 最大的致命傷：資料跟著節點走，不跟著 Pod 走。

---

## 真實事件：MinIO 搬家事件

這個問題在我們的 lakehouse demo 環境中確實發生過，完整的情境如下：

1. MinIO 最初被排程到 **`lakehouse-demo-m02`** 節點上執行，所有的 bucket 和 Iceberg table 資料（Parquet 檔案、metadata JSON）都存放在該節點的 `/home/docker/data/minio`。

2. `lakehouse-demo-m02` 節點因某種原因進入 **`NotReady`** 狀態。Kubernetes 判定節點不可用，最終將 MinIO pod 重新排程到另一個節點 — 控制平面節點（control plane node）。

3. 控制平面節點上的 `/home/docker/data/minio` 是一個**全新的空資料夾**。

4. MinIO 重啟後，看到的是一個乾淨的空目錄，所以它回報的是空的 bucket。從使用者角度來看，資料全都不見了。

實際上，所有資料都好好地待在 `m02` 節點上，只是 MinIO pod 不再跑在那裡了。

---

## 診斷步驟

### 第一步：確認 Pod 目前跑在哪個節點

```bash
kubectl get pod -n minio -o wide
```

輸出範例：

```
NAME                     READY   STATUS    RESTARTS   AGE   IP           NODE
minio-7d9f8b6c5-xk2pq    1/1     Running   0          5m    10.244.0.5   lakehouse-demo
```

注意 `NODE` 欄位。如果顯示的不是原本存放資料的節點，這就是問題所在。

### 第二步：確認資料仍在原節點上

SSH 進入原本存放資料的節點，看看資料還在不在：

```bash
minikube ssh -n lakehouse-demo-m02 -- ls /home/docker/data/minio
```

如果你看到 bucket 資料夾（例如 `lakehouse`、`warehouse` 等），恭喜，資料沒有遺失，只是 Pod 跑錯地方了。

也可以進一步確認 Iceberg 的 Parquet 檔案：

```bash
minikube ssh -n lakehouse-demo-m02 -- find /home/docker/data/minio -name "*.parquet" | head -20
```

### 第三步：比較目前節點與原節點

確認目前 Pod 所在節點的資料夾狀態（以 Pod 被排到控制平面節點為例）：

```bash
minikube ssh -n lakehouse-demo -- ls /home/docker/data/minio
```

如果這個節點的目錄是空的，或者根本沒有這個路徑，就可以確認是節點重排程造成的資料「消失」。

---

## 修復：把 Pod 釘回正確的節點

The fix is to force the MinIO deployment to always run on the node where the data lives, using `nodeName` to pin it to a specific node.

!!! note "nodeName vs nodeSelector"
    `nodeName` 會直接指定 Pod 必須跑在哪個節點，優先於 scheduler 的排程決策。這是快速修復的好方法，但相較於 `nodeSelector` 搭配 label 的做法，彈性較低。

使用 `kubectl patch` 將 deployment 釘到 `lakehouse-demo-m02`：

```bash
kubectl patch deployment minio -n minio --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/nodeName","value":"lakehouse-demo-m02"}]'
```

接著等待 rollout 完成：

```bash
kubectl rollout status deployment/minio -n minio
```

等到看到這行訊息就表示成功：

```
deployment "minio" successfully rolled out
```

---

## 驗證：確認資料回來了

Pod 起來後，確認 MinIO 現在看得到正確的資料。

### 使用 mc（MinIO Client）列出 bucket

```bash
kubectl run mc-verify --rm -it --restart=Never \
  --image=minio/mc:latest \
  --env="MC_HOST_local=http://minio:minio123@minio.minio.svc.cluster.local:9000" \
  -- mc ls local/
```

你應該會看到之前建立的 bucket 重新出現。

### 確認 Iceberg metadata 可以存取

如果你有在跑 Spark 的 job，可以重跑一個簡單的查詢，確認 Iceberg table 還能正常讀取。

---

## 總結與關鍵教訓

| 情境 | 行為 |
|------|------|
| Pod 在同一個節點重啟 | 資料正常，沒有問題 |
| Pod 被排程到不同節點 | 資料「消失」，但實際上還在原節點 |
| 節點進入 NotReady 後恢復 | Kubernetes 不保證 Pod 會回到原節點 |

**核心教訓：hostPath 綁定的是節點，不是 Pod。** 只要 Pod 動了、換節點了，資料就在新節點眼中「不存在」。

!!! warning "開發環境 vs 正式環境的儲存策略"
    在 dev cluster 使用 hostPath 是可以接受的，因為方便快速、零依賴。但在 production 環境：

    - 請使用 **PersistentVolume (PV)** 搭配 **PersistentVolumeClaim (PVC)**，讓儲存與 Pod 的生命週期分離。
    - 考慮使用分散式儲存方案，例如 **Longhorn** 或 **Rook/Ceph**，讓資料可以在節點間複製。
    - 或者，直接使用雲端原生的物件儲存（AWS S3、Google Cloud Storage），完全脫離節點本地磁碟的限制。

如果你在 dev 環境遇到 MinIO 資料消失的情況，先別慌，按照上面的診斷步驟一步步確認，資料大概率還在某個節點上等你。
