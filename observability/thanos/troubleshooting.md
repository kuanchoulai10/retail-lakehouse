# Kubernetes Security Context 與 Volume Permissions 故障排除指南

## 背景故事：一個 Pod 的啟動之旅

想像你是一個容器 (Container)，你的名字叫做 `thanos-receive`。今天你要在 Kubernetes 叢集中啟動，但是你遇到了一個權限問題。讓我們跟著你的啟動過程，一步步了解發生了什麼事。

---

## 第一幕：Pod 的誕生

### 1. Kubernetes 收到部署指令

當管理員執行 `kubectl apply -f thanos-receive-statefulset.yaml` 時，Kubernetes 看到了這個 StatefulSet 配置：

```yaml
securityContext:
  fsGroup: 65534          # 設定檔案系統群組
  runAsUser: 65534        # 容器內程序以此用戶身份運行
  runAsGroup: 65532       # 容器內程序的主要群組
  runAsNonRoot: true      # 禁止以 root 身份運行
```

**這些數字代表什麼？**
- `65534` = `nobody` 用戶（系統預設的無權限用戶）
- `65532` = `nogroup` 群組（系統預設的無權限群組）
- 這是 Linux 系統中的慣例，用來表示「最低權限」的用戶

### 2. Pod 被調度到節點

Kubernetes 調度器選擇了一個節點 `retail-lakehouse-m02`，準備啟動你這個容器。

---

## 第二幕：存儲卷的準備

### 3. 創建 PersistentVolume

由於這是 StatefulSet，Kubernetes 需要為你創建一個持久化存儲：

```yaml
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

**發生了什麼？**
1. Kubernetes 創建了一個 PVC (PersistentVolumeClaim) 叫做 `data-thanos-receive-ingestor-default-0`
2. 儲存系統（如 hostPath、NFS、AWS EBS）分配了 10GB 的空間
3. **關鍵點：這個磁碟區域的擁有者預設是 `root:root` (UID:0, GID:0)**

### 4. 掛載存儲到容器

```yaml
volumeMounts:
  - mountPath: /var/thanos/receive
    name: data
    readOnly: false
```

現在，節點上的某個目錄被掛載到容器內的 `/var/thanos/receive`。

---

## 第三幕：容器啟動與權限衝突

### 5. 容器開始運行

Kubernetes 根據 `securityContext` 設定啟動容器：

```bash
# 在節點上，實際執行的命令類似於：
docker run \
  --user 65534:65532 \  # 以 nobody:nogroup 身份運行
  --mount source=/host/path,target=/var/thanos/receive \
  quay.io/thanos/thanos:v0.39.2 \
  receive --tsdb.path=/var/thanos/receive
```

### 6. 問題發生！

當 `thanos-receive` 程序嘗試啟動時：

1. **程序檢查：** "我需要在 `/var/thanos/receive` 建立 `default-tenant` 目錄"
2. **系統檢查權限：**
   - 目錄 `/var/thanos/receive` 的擁有者：`root:root` (0:0)
   - 目錄權限：`drwxr-xr-x` (755) - 只有 root 能寫入
   - 當前程序身份：`nobody:nogroup` (65534:65532)
3. **結果：** `mkdir /var/thanos/receive/default-tenant: permission denied`

---

## 第四幕：深入理解權限系統

### Linux 檔案系統權限基礎

Linux 中每個檔案和目錄都有：

```bash
drwxr-xr-x  2 root root 4096 Sep  8 21:13 /var/thanos/receive
│││││││││  │  │    │
│││││││││  │  │    └── 群組 (Group)
│││││││││  │  └── 擁有者 (Owner/User)
│││││││││  └── 硬連結數量
│││││││└── 其他人權限 (Others): r-x (讀取+執行，無寫入)
│││││└── 群組權限 (Group): r-x (讀取+執行，無寫入)
││││└── 擁有者權限 (User): rwx (讀取+寫入+執行)
│└── 目錄標記 (d = directory)
```

### Container 中的用戶身份

當容器以 `runAsUser: 65534` 運行時：

```bash
# 在容器內執行
$ id
uid=65534(nobody) gid=65532(nogroup) groups=65532(nogroup),65534(nobody)

# 嘗試寫入掛載的目錄
$ mkdir /var/thanos/receive/test
mkdir: cannot create directory '/var/thanos/receive/test': Permission denied
```

### fsGroup 的作用

`fsGroup: 65534` 告訴 Kubernetes：

> "請將所有掛載的 volume 的群組擁有者改為 65534，並設定群組可寫入權限"

**但是！** 這個功能需要：
1. 儲存驅動程式支援 (不是所有 StorageClass 都支援)
2. 正確的 `fsGroupChangePolicy` 設定
3. 在我們的案例中，可能沒有生效

---

## 第五幕：解決方案詳解

### 方案一：使用 initContainer (推薦)

```yaml
initContainers:
- name: init-chmod-data
  image: busybox:1.36
  command: ['sh', '-c', 'chmod 775 /var/thanos/receive && chown 65534:65532 /var/thanos/receive']
  securityContext:
    runAsUser: 0          # 以 root 身份運行，有權限修改檔案擁有者
    runAsNonRoot: false
  volumeMounts:
  - name: data
    mountPath: /var/thanos/receive
```

**為什麼這樣可以？**
1. initContainer 在主容器啟動前運行
2. 以 root 身份執行，有權限修改檔案擁有者
3. 將目錄擁有者改為 `nobody:nogroup` (65534:65532)
4. 設定權限為 775 (擁有者和群組都可寫入)
5. 主容器啟動時就能正常寫入了

### 方案二：修改 SecurityContext

```yaml
securityContext:
  fsGroup: 65534
  # 移除以下兩行，讓容器以 root 運行
  # runAsUser: 65534
  # runAsNonRoot: true
```

**權衡考量：**
- ✅ 簡單直接
- ❌ 降低安全性（容器以 root 運行）
- ❌ 違反最小權限原則

### 方案三：使用 emptyDir

```yaml
volumes:
- name: data
  emptyDir: {}  # 不使用持久化存儲
```

**適用場景：**
- ✅ 測試環境
- ✅ 不需要資料持久化的場景
- ❌ 生產環境（資料會遺失）

---

## 實戰檢查清單

### 診斷步驟

1. **檢查 Pod 狀態**
   ```bash
   kubectl get pods -n thanos
   kubectl describe pod <pod-name> -n thanos
   ```

2. **檢查容器日誌**
   ```bash
   kubectl logs <pod-name> -n thanos --previous
   ```

3. **檢查檔案權限**
   ```bash
   # 如果 Pod 能啟動，進入檢查
   kubectl exec -it <pod-name> -n thanos -- ls -la /var/thanos/
   kubectl exec -it <pod-name> -n thanos -- id
   ```

4. **檢查 PVC 狀態**
   ```bash
   kubectl get pvc -n thanos
   kubectl describe pvc <pvc-name> -n thanos
   ```

### 權限問題的常見症狀

- Pod 處於 `CrashLoopBackOff` 狀態
- 日誌顯示 `permission denied` 錯誤
- 容器無法創建檔案或目錄
- 程序啟動失敗

### 預防措施

1. **使用 initContainer** - 最安全的方法
2. **設定正確的 fsGroup** - 確保儲存支援
3. **測試權限設定** - 在部署前驗證
4. **遵循最小權限原則** - 不要隨便使用 root

---

## 總結

這個問題的核心是 **容器的執行身份** 與 **檔案系統權限** 不匹配：

- **容器**：以 `nobody` (65534) 身份運行
- **檔案系統**：掛載的目錄擁有者是 `root` (0)
- **結果**：無權限創建檔案/目錄

通過理解 Linux 權限系統、Kubernetes SecurityContext 和 Volume 掛載機制，我們可以選擇合適的解決方案來確保容器既安全又能正常運行。

**記住：安全性和功能性需要平衡，initContainer 方案在大多數情況下是最佳選擇。**