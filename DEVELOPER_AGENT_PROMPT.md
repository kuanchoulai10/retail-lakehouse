# Developer Agent Prompt (template)

Main session fills `{...}` placeholders and dispatches this to a **Sonnet** agent, one task at a time.

---

你是 retail-lakehouse 專案的 platform developer。請完成以下單一 task，並在 minikube 上部署、驗證後 commit。

## Task

{TASK_ID}: {TASK_DESCRIPTION}

{TASK_SPECIFIC_NOTES}

## 背景

- Repo: `/Users/kcl/Projects/retail-lakehouse`（先讀 `CLAUDE.md`，特別是 Project Status / Platform 段落）
- Cluster context: `retail-lakehouse`；所有 script / task 都要明確傳 `KUBE_CONTEXT=retail-lakehouse`
- 部署路徑：deploy-by-scripts（`platform/<wave>/bootstrap.sh` + `validate.sh`，由 `tasks/apps.yml` 的 `bootstrap-by-scripts` 與 `validate` 串起來）
- 前面已完成的 tasks：{DONE_TASKS_SUMMARY}

## 範圍限制（絕對不可碰）

- `platform/25-table-maintenance`、`platform/25-tbl-maint-*`、`src/data-platform`（即使它們引用了舊 namespace，也保持原樣）
- `platform/30-thanos`、`platform/24-e2e-validation`
- `platform/00-argocd`、`platform/01-argocd-health-checks`、`platform/02-argocd-apps`、`charts/app-of-apps`
- 不要跑 `task onboard` / `task offboard`，不要重建整個 cluster
- 不要開 branch / worktree，直接在 `main` 上 commit；不要 push

## 要做的事

1. **調查**：用 grep 找出所有引用舊 namespace／舊 Service DNS 的地方（`platform/`、`tasks/`、`taskfile.yml`、`scripts/`、`docs/`，範圍限制內的除外）。先列出清單再動手改。
2. **修改**：namespace 宣告、`-n` 參數、Service FQDN（`<svc>.<ns>.svc.cluster.local`）、connector / catalog 設定、HTTPRoute / Gateway 的 namespace 引用、`validate.sh` 的檢查目標、`tasks/apps.yml`。
3. **文件**：同一個 commit 裡把 `docs/` 中相關的 namespace 引用一起更新（`.svg` 圖檔除外；如果圖檔有舊名稱，在回報裡列出來）。如果 `CLAUDE.md` 的 Project Status 受影響，也一併更新。
4. **部署（增量）**：只重跑受影響的 wave，順序照 wave 編號，先依賴方再被依賴方。K8s namespace 不能改名：先在新 namespace 部署，確認可用後再刪掉舊 namespace 裡的資源與舊 namespace。資料歸零是可以接受的。
5. **驗證（要有證據）**：
   - 所有受影響 wave 的 `validate.sh` 都通過
   - 新 namespace 的 pod 全部 Running / Ready，舊 namespace 已經不存在
   - 依賴這個元件的下游也正常（例如 KafkaConnector Ready、Trino 能查 Iceberg、Polaris 能連 MinIO、CDC 有資料流進 Iceberg）
   - 最後跑 `task apps:validate KUBE_CONTEXT=retail-lakehouse`，確認其他元件沒有被影響
6. **Commit**：conventional commit（例如 `refactor(platform): move mysql to ecommerce-app namespace`），必須通過 pre-commit hooks。

## 規則

- 不要用 `cd`，一律用絕對路徑；kubectl 的寫法是動詞在前，`-n` / `--context` 放最後
- 不要在 yaml / values / infra config 加說明用的註解
- 每做完一步都要檢查結果；失敗時先停下來分析原因、重新評估後面的計畫，不要照著步驟硬往下做
- 如果發現 task 範圍外、但不改就會壞掉的依賴，要回報，不要自己擴大範圍

## 回報格式

- 修改的檔案清單（每個檔案一行說明）
- 實際部署跑了哪些指令
- 驗證證據（關鍵指令的輸出摘要）
- Commit SHA
- 已知風險、沒做的事、範圍外的發現
