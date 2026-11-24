# Writing Linear issues

Planned work for this project lives in Linear (team `KCL10`, issue keys `KCL-<n>`). The local `.scratch/` tracker in `issue-tracker.md` is for skills that publish markdown issues; when the user asks for a Linear issue, follow this file.

## Language and voice

- Write in Traditional Chinese (繁體中文). Technical terms stay in English (`snapshot`, `partition spec`, `Temporal schedule`).
- Say what the change is and what it means for the user in plain words. Code identifiers, file paths, env vars and API routes belong in **技術細節**, in backticks; keep them out of the user story.
- One issue covers one change that can be reviewed on its own. Split a request that mixes several pages or decisions.

## The six sections

Every issue description has exactly these six `##` sections, in this order:

1. `## User story`: 「身為 <誰>，我想要 <什麼>，這樣 <得到什麼>」. Use a real role: 平台使用者, 表的負責人, 平台維運者. Write two stories when two roles care.
2. `## 現狀與困難`: what happens today, checked against the code, and why it is a problem.
3. `## 打算怎麼做`: the intended change, as the user will see it. For an issue still under discussion, title it `## 打算怎麼做（候選做法，待討論）`, list the candidate approaches and end with the questions still open.
4. `## 技術細節`: files, aggregates, API routes, settings and the mechanism the change touches, found by reading the code, not guessed.
5. `## 需要注意的事`: risks, edge cases, ordering dependencies on other issues, and rules in `CLAUDE.md` files the change must respect or update.
6. `## 完成條件`: a checklist (`- [ ]`). Include tests and stories; add a minikube check when the backend or cluster behaviour changes, and when that check qualifies as an e2e scenario (root `CLAUDE.md`, "Cluster checks become e2e scenarios") the box is the scenario passing on the cluster, named by its file. A discussion issue ends with deciding (often as an ADR) and splitting into implementation issues.

## Labels, titles and placement

- **Type label:** one of `Feature`, `Improvement`, `Bug`.
- **`需要討論`:** add it when the direction is not decided yet. Prefix the title with `【需要討論】` and open the description with the quote line `> 這張 issue 先記錄，之後討論。`
- **Titles:** state the outcome in plain words (`Tables 頁面拿掉 Rule 欄`), not the implementation.
- **Projects:** user-visible work joins a project and milestone by theme: `Console 一看就懂` (P-KCL-8), `Discovery policy` (P-KCL-7) and `表自己保持健康，不用人盯` (P-KCL-6). A cross-cutting design question that is not ready for a project stays in Backlog with no project.
- **Status:** new issues start in `Backlog`.
- **Relations:** link related issues. Use *blocked by* when one cannot start before another decides or lands.

## Changing an existing issue

**Never rewrite an existing issue's description to record a new decision.** Add a comment instead, dated (`**範圍變更（YYYY-MM-DD）：**` or `**補充（YYYY-MM-DD）：**`). The comment names what is now void in the description and links the issues behind the change. The history of what was decided stays readable.

## Before creating

- Show the user the drafts and the proposed placement when they ask to review them first. Create in Linear only after they approve.
- Report back the issue keys, where each one landed, and every comment or relation you added to existing issues.
