# Troubleshooting: Minikube Worker Node 無法拉取外部 Container Image

> **適合讀者**：在公司或特定網路環境下跑 Minikube 的開發者。這篇說明為什麼 Minikube worker node 有時候連不上 `registry.k8s.io` 或其他外部 container registry，以及本專案如何繞開這個問題。

---

## 症狀 Symptom

重啟 Minikube 後，你發現某些 pod 一直停在 `Pending` 或 `ImagePullBackOff` 狀態：

```bash
kubectl get pods -A
```

```
NAMESPACE      NAME                          READY   STATUS             RESTARTS
kube-system    coredns-xxxxx                 0/1     Pending            0
kube-system    metrics-server-xxxxx          0/1     ImagePullBackOff   3
```

在 Minikube 啟動日誌或 node 事件裡，看到這樣的訊息：

```
Failing to connect to https://registry.k8s.io/ from inside the minikube container
```

或是 pod events：

```bash
kubectl describe pod coredns-xxxxx -n kube-system
```

```
Events:
  Warning  Failed  ...  Failed to pull image "registry.k8s.io/coredns/coredns:v1.11.1":
                         rpc error: code = Unknown desc = context deadline exceeded
```

---

## 根本原因

### Minikube 跑在 Docker 容器裡

使用 Docker driver 時（Mac 上的預設值），Minikube 的每個 node 其實是一個 **Docker 容器**。這些容器的網路設定繼承自 Docker daemon，但不一定繼承你 host 機器的 proxy 設定。

問題的核心是：**Minikube 容器的出口網路可能被防火牆、proxy 或 NO_PROXY 設定阻擋**，無法連到 `registry.k8s.io`、`docker.io` 等外部 registry。

### NO_PROXY 設定錯誤

在需要 proxy 的網路環境下，Minikube 啟動時會設定 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY` 環境變數。常見的問題是 `NO_PROXY` 只包含了內部 IP，但沒有正確 bypass 讓 Minikube 可以直連外部的 DNS 或 registry：

```
# 典型的不完整 NO_PROXY 設定
NO_PROXY=192.168.85.2,192.168.85.3
```

這個設定告訴系統：這兩個內部 IP 直接連，其他全部走 proxy。但如果 proxy 本身也連不到 `registry.k8s.io`，image pull 就會失敗。

!!! info "這是環境差異問題，不是 Minikube bug"

    在家裡的網路直接跑 Minikube 通常沒問題，因為沒有 proxy。但在公司網路或 VPN 環境下，proxy 的存在就會影響 Minikube 容器的對外連線能力。

---

## 本專案的解決策略：使用本地 Registry

本專案不依賴 worker node 拉取外部 image，改用 **Minikube 的內建本地 registry**（port 5000）來分發自製 image。

### 架構示意

```
你的 Mac (host)
    │
    │  docker build → image
    │
    ▼
localhost:5000 (Minikube 本地 registry，透過 port-forward)
    │
    │  push
    ▼
Minikube 內部 registry (registry.kube-system.svc.cluster.local:80)
    │
    ◄── SparkApplication/Deployment 直接從 registry 拉取
        不需要連外網
```

### 啟用方式

```bash
# 啟動時加上 registry addon
minikube addons enable registry -p lakehouse-demo
```

啟用後，Minikube 會在 `kube-system` namespace 裡跑一個 registry 服務。透過 port-forward 就可以從 host 推送 image：

```bash
# 建立 port-forward（背景執行）
kubectl port-forward svc/registry -n kube-system 5000:80 &

# 推送 image 到本地 registry
docker push localhost:5000/table-maintenance-jobs:latest
```

`SparkApplication` manifest 裡的 image 就直接寫：

```yaml
spec:
  image: localhost:5000/table-maintenance-jobs:latest
  imagePullPolicy: Never  # 不拉外部，使用本地
```

!!! tip "`imagePullPolicy: Never` vs `IfNotPresent`"

    在 Minikube 本地開發時，使用 `Never` 確保 Spark Operator 完全不嘗試連外部 registry，避免任何因網路問題導致的 pull 失敗。只有本地 registry 裡有對應 image 才能正常跑。

---

## 如果你仍需要拉取外部 image

有些系統 image（`coredns`、`kube-proxy` 等）在 Minikube 初始化時就需要，沒辦法走本地 registry。這種情況有幾個處理方向：

### 選項一：重新設定 Proxy

如果你的環境是 proxy 問題，可以在啟動 Minikube 時帶入正確的 proxy 設定：

```bash
minikube start -p lakehouse-demo \
  --docker-env HTTP_PROXY=http://your-proxy:port \
  --docker-env HTTPS_PROXY=http://your-proxy:port \
  --docker-env NO_PROXY=localhost,127.0.0.1,10.96.0.0/12,192.168.0.0/16
```

`NO_PROXY` 裡的 CIDR 需要包含 Kubernetes 的 service CIDR 和 pod CIDR，確保 cluster 內部流量不走 proxy。

### 選項二：預先快取 Image

在網路正常的環境下，用 `minikube image load` 把需要的 image 預先打包進 Minikube node：

```bash
# 先在有網路的環境 pull image
docker pull registry.k8s.io/coredns/coredns:v1.11.1

# 載入 Minikube
minikube image load registry.k8s.io/coredns/coredns:v1.11.1 -p lakehouse-demo
```

Image 載入後，對應 pod 的 `imagePullPolicy` 要設為 `IfNotPresent`，才不會繞過本地快取重新去拉。

### 選項三：重建 Minikube Profile（最後手段）

如果系統 image 已經損毀或遺失，且 proxy 設定難以修正，重新建立 Minikube profile 是最乾淨的方式：

```bash
minikube delete -p lakehouse-demo
minikube start -p lakehouse-demo \
  --cpus=6 \
  --memory=12288 \
  --nodes=3 \
  --driver=docker \
  --addons=registry
```

!!! warning "重建會清除所有 Persistent Data"

    `minikube delete` 會清除所有 node 的資料，包含 MinIO 的 hostPath 資料。如果 MinIO 上有重要的測試資料，先備份再操作：

    ```bash
    # 備份 MinIO 資料
    minikube ssh -n lakehouse-demo-m02 \
      -- tar czf /tmp/minio-backup.tar.gz /home/docker/data/minio
    minikube cp lakehouse-demo-m02:/tmp/minio-backup.tar.gz ./minio-backup.tar.gz
    ```

---

## 診斷流程

```
kubectl get pods -A 出現 ImagePullBackOff
        │
        ▼
kubectl describe pod <pod> 看 Events
        │
        ├─ "Failed to pull image ... connection refused"
        │   → 本地 registry 沒有跑，或 port-forward 沒開
        │
        ├─ "Failed to pull image ... registry.k8s.io ... context deadline exceeded"
        │   → 網路問題，worker node 連不到外部 registry
        │   → 考慮用 minikube image load 預先載入
        │
        └─ "Failed to pull image ... 401 Unauthorized"
            → Image 存在但需要認證（private registry）
            → 設定 imagePullSecrets
```

---

## 快速總結

| 情境 | 建議方案 |
|------|---------|
| 自製 image（table-maintenance-jobs 等） | 使用 Minikube 本地 registry（`localhost:5000`），`imagePullPolicy: Never` |
| 系統 image pull 失敗（coredns 等） | 用 `minikube image load` 預先載入，或修正 proxy 設定 |
| 在有 proxy 的公司網路 | Minikube 啟動時帶 `--docker-env` 設定正確的 proxy 和 NO_PROXY |
| 以上都試了還是不行 | `minikube delete` + 重建 profile（備份資料後再操作） |

本專案的 image 全部走本地 registry，日常開發不需要依賴外部 registry 連線。只有在初次建立 Minikube 環境、或系統元件更新時才需要對外拉取。
