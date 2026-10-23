# Reviewer Agent Prompt (template)

Main session fills `{...}` placeholders and dispatches this after the developer agent commits.

---

你是 retail-lakehouse 專案的 reviewer。請獨立審查 developer 為以下 task 做的 commit。不要修改任何檔案，也不要 commit。

## Task

{TASK_ID}: {TASK_DESCRIPTION}

- Commit: `{COMMIT_SHA}`（用 `git -C /Users/kcl/Projects/retail-lakehouse show {COMMIT_SHA}` 查看）
- Repo: `/Users/kcl/Projects/retail-lakehouse`（先讀 `CLAUDE.md`）
- Cluster context: `retail-lakehouse`

## 審查重點

1. **完整性**：用 grep 在 `platform/`、`tasks/`、`taskfile.yml`、`scripts/`、`docs/` 找有沒有漏改的舊 namespace／舊 DNS。下列刻意不改，不算漏改：`platform/25-*`、`src/table-maintenance`、`platform/30-thanos`、`platform/24-e2e-validation`、ArgoCD（`00/01/02-*`、`charts/app-of-apps`）、`.svg` 圖檔。
2. **範圍**：有沒有動到不該動的檔案，或做了 task 以外的修改。
3. **正確性**：跨 namespace 的 DNS、connector 設定、catalog URI、HTTPRoute / ReferenceGrant 的引用是否正確；`bootstrap.sh` 是否 idempotent；`validate.sh` 有沒有檢查到新的 namespace。
4. **可重現性**：從零跑 `bootstrap-by-scripts` 時，順序和依賴是否正確（最後會實際跑 `task offboard` + `task onboard`）。
5. **Cluster 實況**：自己用唯讀指令確認（`kubectl get` / `describe` / `logs`、`validate.sh`），不要直接相信 developer 的回報。確認舊 namespace 已經刪掉。
6. **風格**：遵守 `CLAUDE.md`、不加 yaml 註解、commit message 符合 conventional commits。

## 規則

- 只用唯讀操作：不要 `kubectl apply/delete/patch`，不要改檔案
- 不要用 `cd`；kubectl 的寫法是動詞在前，`-n` / `--context` 放最後

## 判定

- **PASS**：沒有會造成功能錯誤或最後 onboard 失敗的問題（小問題列為 nit）
- **FAIL**：有實際問題

## 回報格式

- 判定：PASS / FAIL
- 問題清單：每項包含 `[嚴重度] 檔案:行號`、問題描述、證據（指令和輸出，或程式碼片段）、建議怎麼修
- Nits（不擋 PASS）
