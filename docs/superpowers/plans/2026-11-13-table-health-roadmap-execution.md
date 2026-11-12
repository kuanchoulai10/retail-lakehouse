# Table health roadmap: execution plan

> **For the main session.** This plan runs the five milestones of the Linear project P-KCL-6 「表自己保持健康，不用人盯」. It does not hold code; each milestone has its own implementation plan, written by the main session when the milestone starts. Milestone 1's is `docs/superpowers/plans/2026-11-13-milestone-1-timeout-fencing.md`.

**Goal:** build milestones 1 → 5 in order, each implemented by one subagent, reviewed, verified on the minikube cluster, and recorded in Linear; finish with a summary comment on the project.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` (binding). Linear project P-KCL-6 holds the goal and references; its issues hold the per-issue design decisions under "## 設計決定（2026-11-13）".

## Global Constraints

- Milestones run strictly in order: 1 (KCL-46, 47), 2 (KCL-48..52), 3 (KCL-53..57), 4 (KCL-58..60), 5 (KCL-61..63).
- Work on `main`, local commits only, never push. Commits use explicit paths, conventional subjects, and end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- Every commit passes `pytest`, `ty check`, `ruff check .`, `lint-imports` (backend) and the frontend unit tests when the console changes; TDD always.
- No new dependency without asking the user. No explanatory comment blocks in `values.yaml` or infra configs. Never edit `.claude/settings*.json`, never run `sops`, never touch `platform/30-thanos`, `platform/24-e2e-validation`, the ArgoCD path, the untracked `.claude/worktrees/`, or the Spark operator's leader election.
- Shell: no `cd`; `uv run --project src/data-platform/backend --directory src/data-platform/backend ...`; `KUBE_CONTEXT=retail-lakehouse` on every script and Taskfile call; `kubectl <verb>` before its flags.
- The user reads Chinese: every report to the user, and every Linear comment, is written in Traditional Chinese, in plain words about what changed and its impact, not code identifiers.
- A design detail the spec leaves open is decided by whoever meets it, with the reasoning posted as an issue comment; work does not stop to ask.

## Roles

**Main session.** Writes each milestone's plan, sets Linear statuses, dispatches the implementer and the reviewer, rules on conflicts, redeploys and verifies on the cluster, decides the rebuild size and whether the e2e grows, keeps the ledger, monitors the cluster during every verification and e2e run and reports what it sees without being asked.

**Milestone implementer** (one fresh `general-purpose` subagent per milestone, model `opus`). Reads the Linear project and the milestone's issues with the `mcp__linear-server__*` tools (`get_project`, `get_issue`, `list_comments`), the spec and the milestone plan; implements the plan task by task with TDD and one commit per task; posts progress, findings, decisions and blockers as comments on the issue they concern (`save_comment`) while it works; does not change issue statuses; dispatches no subagents; does not deploy to the cluster. It writes its full report to the ledger directory and returns only status (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`), commit list, a one-line test summary and its concerns.

**Milestone reviewer** (fresh `superpowers:code-reviewer`-style subagent, model `opus`). Gets the spec path, the milestone plan path, the implementer's report path and a review package (`git log --oneline`, `git diff --stat`, `git diff -U10` for `BASE..HEAD`, in one file). Returns findings ranked by severity with file and line, and a verdict on spec compliance and on quality.

## Ledger

`.superpowers/sdd/table-health-roadmap/progress.md` (git-ignored). First line: `# SDD ledger — plan: docs/superpowers/plans/2026-11-13-table-health-roadmap-execution.md`. One line per event: `Milestone N: plan committed <sha>`, `Milestone N: BASE <sha>`, `Milestone N: implementer DONE <first>..<last>`, `Milestone N: review round R <verdict>`, `Milestone N: deployed <small|large>`, `Milestone N: verified`, `Milestone N: complete`, and every `Ruling: <what> — <why> — <cost if wrong>`. After a context compaction, trust the ledger and `git log` over memory: a milestone with a `complete` line is never redone.

Implementer briefs and reports live beside it: `milestone-N-brief.md`, `milestone-N-report.md`, `milestone-N-review-package.md`, `milestone-N-review.md`.

## Per-milestone loop

- [ ] **1. Plan.** For milestones 2–5, write `docs/superpowers/plans/2026-11-13-milestone-N-<slug>.md` with the `superpowers:writing-plans` structure, from the spec, the milestone's Linear issues and the code as milestone N−1 left it; self-review it; commit it (`docs(table-maintenance): plan milestone N ...`). Ledger the commit.
- [ ] **2. Start in Linear.** Set the milestone's issues to In Progress. Ledger `BASE` (`git rev-parse HEAD`).
- [ ] **3. Dispatch the implementer.** The dispatch carries: one line on where the milestone sits in the roadmap; the paths of the spec and the milestone plan ("read these first; the plan holds the exact values"); the Linear project id and the milestone's issue ids; the Global Constraints above; the report path and the report contract; the rule that it posts issue comments as it goes. Never paste earlier milestones' history.
- [ ] **4. Handle the report.** `BLOCKED` or `NEEDS_CONTEXT`: supply the context or rule on the plan defect, ledger it, resume the same implementer with `SendMessage`. `DONE_WITH_CONCERNS`: read the concerns; correctness concerns are handled before review.
- [ ] **5. Read Linear.** Read the comments the implementer posted; correct anything wrong; set issues whose work is committed to In Review.
- [ ] **6. Review.** Build the review package for `BASE..HEAD`, dispatch the reviewer. For findings: rounds 1–3 resume the implementer with the findings file; rounds 4–5 a fresh implementer; each round ends with a scoped re-review. A finding still open after round 5 is ruled on and, if not fixed, written as a risk on its issue.
- [ ] **7. Gates.** `task gates:pre-pr KUBE_CONTEXT=retail-lakehouse` passes on the final tree.
- [ ] **8. Deploy.** Judge the size and ledger the judgement with its reason.
  - **Small** (only wave 25 changes: backend, Spark image, console, the wave-25 chart): `KUBE_CONTEXT=retail-lakehouse platform/25-lakehouse-control-plane/build.sh`, then `KUBE_CONTEXT=retail-lakehouse platform/25-lakehouse-control-plane/bootstrap.sh`.
  - **Large** (another wave's bootstrap, a new platform component, the cluster bring-up path, or a change whose first deploy cannot be tried on the running cluster): `task offboard KUBE_CONTEXT=retail-lakehouse`, `task onboard KUBE_CONTEXT=retail-lakehouse` (8 CPUs, 26 GB), then the full e2e `KUBE_CONTEXT=retail-lakehouse platform/25-lakehouse-control-plane/e2e.sh`, which must exit 0.
- [ ] **9. Verify the milestone.** Run the milestone plan's verification section on the cluster, forcing the rare event it names. Watch the cluster the whole time (Monitor on pods, restarts and load) and tell the user what you see. Post the evidence (commands, observed values, Temporal workflow ids) as a comment on each issue. What cannot be verified is written as a risk on its issue; work moves on.
- [ ] **10. Decide the e2e.** Ask: does a regression in this milestone's behaviour stay invisible to the existing e2e, and can a check be added without a second concurrent Spark job or a cluster-wide setting change? If yes, add it in its own commit (`test(lakehouse-control-plane): ...`) and run the e2e once more. Ledger the decision either way.
- [ ] **11. Docs.** Add a line to `docs/agents/project-history.md`; update the topic file the milestone changes (`src/data-platform/backend/CLAUDE.md`, `platform/CLAUDE.md`, `src/data-platform/frontend/CLAUDE.md`); list new risks in `docs/agents/known-follow-ups.md`. Commit.
- [ ] **12. Close in Linear.** Issues verified → Done; issues done with a written risk → Done with the risk linked in a comment; issues not done → back to Todo with a comment saying why. Ledger `Milestone N: complete`. Tell the user in two or three sentences what landed and what risk is open, then start the next milestone without waiting.

## Finish

- [ ] After milestone 5: post one comment on the Linear project P-KCL-6 summarising all five milestones: what each delivered, how it was verified, the open risks with their issues, and the follow-ups. Write it in Traditional Chinese.
- [ ] Final report to the user: the same summary, the commit range, and anything that needs their decision.

## What stops the run

Only these: an irreversible or destructive action outside the plan (a deletion the plan does not name, anything beyond `task offboard` of this cluster); a push, publish or other outward action; a plan so broken that every path forward is a guess. Everything else is a ruling in the ledger.
