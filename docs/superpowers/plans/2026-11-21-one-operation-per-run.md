# One Operation Per Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Written 2026-11-21 against HEAD `a39f5541`** (KCL-94's last docs commit). A small KCL-94 fix wave may land after it. Every file this plan names was read at that HEAD; read it again at the HEAD you start from before changing it.

**Goal:** A maintenance run does one operation on one table. Its attempts are its timeline, and it records the parameters it passed to the Iceberg procedure and the numbers the procedure returned. When a reconciliation finds several operations due, the table's maintenance workflow opens one run per operation and runs them one after another in the fixed order, still one Spark job at a time per table. The Maintenance, Reconciliations and Commits tabs open a record in a side panel next to the list. The url names the open record, old links to a run open its panel, and at phone width the panel takes the whole page.

**Architecture:**
- `TableMaintenanceRun` takes in what `OperationRun` held. `operation`, one stored `RunStatus`, `filters`, `procedure_args`, `metrics`, `error`, `skip_reason` and `attempts` all sit on the run. `OperationRun`, `OperationRunStatus` and `partially_failed` are deleted.
- The reconciliation workflow mints one `mr-` id for each planned operation and starts the table's one `TableMaintenanceWorkflow` with all of them. The child workflow:
  - creates every run as `pending` before its first submit;
  - runs the runs in order;
  - deletes a run's Spark jobs when that run ends;
  - skips the runs it never reached.
- Each reconciliation operation that started a run keeps that run's id. `GET /v1/table-reconciliations/{id}` reads one record.
- The design system gets three things:
  - `Drawer` gains a non-modal side-panel mode, which becomes modal and full width below 768px;
  - `DataTable` rows can open in a panel;
  - `DescriptionList` is new.
- The three tabs keep the open record in the url: `?run=`, `?reconciliation=` and `?snapshot=`.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK, React + TanStack Query + orval + MSW, Radix, Tailwind 4, Storybook/vitest.

**Spec:**
- Linear KCL-95 (https://linear.app/kcl10/issue/KCL-95), with the KCL-80 decisions (2026-11-17, confirmed 2026-11-19) and the KCL-70 side-panel decision (2026-11-19) it quotes.
- What it builds on:
  - KCL-93 (plan `docs/superpowers/plans/2026-11-20-per-table-maintenance-workflow.md`): one maintenance workflow per table, raises, fencing and the report to the parent.
  - KCL-94 (plan `docs/superpowers/plans/2026-11-20-partition-selected-compaction.md`): `OperationRun.filters`, `waiting_for_writes` and the Maintenance tab's Scope line and attempts caption.
- ADR 0011 (prefixed ids) and ADR 0012 (policies; the operation order).
- **Read each file at HEAD before changing it; never apply a step against a remembered version.**

`<pytest>` is `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`. `<vitest>` is `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run`. `<ds-vitest>` is `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system test -- --run`.

## Global Constraints

Decisions this plan makes are marked **(decided)** with the reason. The rest was settled in KCL-80, KCL-70 or by the user for this plan, and is not reopened.

### The run

- **One run is one operation (user).** A record is "one table + one operation", and its attempts stay under it as its timeline.
- **The run has these fields:** `id`, `table_uuid`, `trigger`, `operation: MaintenanceOperation`, `priority`, `execution_ref`, `created_at`, `status: RunStatus`, `filters: tuple[SpecFilter, ...]`, `procedure_args: dict[str, Any]`, `metrics: dict[str, Any]`, `error: str | None`, `skip_reason: str | None`, `finished_at`, `attempts: tuple[OperationAttempt, ...]`.
  - `started_at` is a property: the first attempt's `started_at`, `None` before the first submit **(decided: a run created `pending` has not started; KCL-80's sketch has `started_at`)**.
- **One status (user).** `RunStatus` is `pending`, `queued`, `running`, `succeeded`, `failed`, `skipped`. There is no `partially_failed`. It is stored, not derived **(decided: with one operation there is nothing to derive it from)**.
  - An attempt's `status` is a `RunStatus` too. A validator allows it only `queued`, `running`, `succeeded` or `failed` **(decided: one status vocabulary for the API and the console's tones)**.
- **Names kept (decided):**
  - `OperationAttempt` keeps its name, since it is still the attempt of the run's operation.
  - `metrics` keeps its name: it is the key the Spark runtime posts and the e2e reads, `completed_without_callback` included. KCL-80's word "result" names what it holds.
- **`job_name` moves onto `OperationAttempt` (decided: every attempt has its own SparkApplication, and at HEAD only the last one's name was kept).**
- **Deleted:**
  - `OperationRun.expected_files`, which nothing ever sets;
  - `_finished_history`, the tolerance for runs stored before attempt history existed. There is no migration.
- **Parameters (user):** the run records what it passes to the procedure.
  - `filters`: the compaction `where` clauses, one per partition spec, `()` for the whole table. Only `rewrite_data_files` may carry them (`InvalidRunTransition`, as in KCL-94).
  - `procedure_args`: the dict `maintenance_procedure_args.py` builds at plan time, for example `older_than` and `retain_last` for `expire_snapshots` **(decided: kept as JSON, the exact arguments Spark is called with; typing them per operation is a follow-up)**.
  - The numbers the procedure returns stay in `metrics`. No per-partition list is recorded.
- **A skipped run says why in `skip_reason`, and `error` holds only a failure's error (decided: the reconciliation record already names its skip reason `skip_reason`).** The one reason this plan writes is `the table's maintenance stopped before this run started`.
- **No `retrying` status (decided: KCL-80 lists the statuses and adds none).** A run whose attempt failed and will be retried still reads `failed` during the backoff. `docs/agents/known-follow-ups.md` already lists this, and the entry is reworded for one operation per run.

### The workflow

- **One child workflow per plan runs the plan's runs in order (decided).** The parent starts one `TableMaintenanceWorkflow` under the table's fixed id, as at HEAD, and the child runs one run per planned operation.
  - Why: it keeps the plan → child → report contract and KCL-80's "the table's workflow does the operations in order". It also keeps a queue of runs out of the parent's state, which continue-as-new would have to carry.
  - Rejected: the parent starting one child per run.
- **The order is the plan's (ADR 0012):** `rewrite_data_files` → `rewrite_manifests` → `expire_snapshots` → `remove_orphan_files`. The plan already lists operations in `MaintenanceOperation.ordered()` order.
- **The parent mints the ids.**
  - The `rc-` id is minted before planning, as at HEAD.
  - One `mr-` id per planned operation is minted after the plan returns **(decided: only the plan knows how many runs there are; ids minted in the parent are in its history, so the reconciliation record links each operation before the child reports)**.
  - `TableMaintenanceWorkflowInput.run_ids: list[str]` replaces `run_id`, one id per plan operation, in order. The child pairs them with `zip(..., strict=True)`. The parent is the only caller.
- **Every run is created up front (decided).** The child creates all its runs, `pending`, in plan order, before its first submit. Every run id the reconciliation links then exists at once, and waiting runs show as Pending. GitHub Actions shows a workflow run's queued jobs, and Airflow a DAG run's scheduled tasks, in the same way.
  - If any create fails, the child submits nothing, and the runs it already created are skipped.
- **One at a time (KCL-80).** Run k+1's first submit comes after:
  - run k's last attempt is recorded;
  - run k's Spark jobs are deleted.
  - **(decided)** A run's jobs are deleted when it ends, not at the end of the plan. This frees the executors kept for OOM evidence before the next job queues.
- **A failed run does not stop the next one**, as at HEAD for operations.
- **The runs never reached are skipped at `_finish`** through the new activity `SKIP_MAINTENANCE_RUN` (`skip_maintenance_run`). The workflow reaches `_finish` on cancel, on give-up, after a create failure or after a submit failure that ends the workflow.
  - A skip of a run that is no longer pending changes nothing and returns `skipped: false` **(decided: a retried activity whose first try landed must not fail)**.
- **Results are keyed `(operation, attempt)`, as at HEAD (decided: an operation appears once in a plan, so the key stays unique and the attempt bookkeeping is unchanged).** A result signal is kept only when its `run_id` is the id of that operation's run, and is logged and dropped otherwise. `OperationResultSignal` is unchanged.
- **A raise reaches every unfinished run of the plan (decided: the runs not started yet would otherwise submit at the old priority).**
  - The current run is raised first, then the runs still `pending`, in order. That is at most four `RAISE_MAINTENANCE_RUN_PRIORITY` calls.
  - Only the current run's reply (`raised`) decides whether its queued attempt is requeued.
  - A failed raise of any of them sets `_dropped_raise`, so the report says a raise was left unapplied, as at HEAD.
- **The report to the parent carries `run_ids`, and the parent matches it by equality.**
  - The parent's `in_flight_run_id` becomes `in_flight_run_ids: list[str] | None`, in its state, in its `state()` query and in its continue-as-new input.
  - `_given_up_run_id` becomes `_given_up_run_ids`.
- **No new `workflow.patched` (decided: no migration, the cluster is rebuilt).** The existing patches stay as they are.
- **The `MaintenanceOperations` search attribute is unchanged, and no new attribute is added (decided).** The Temporal execution still runs every operation of its plan, so its keyword list stays true. A run finds its execution by `execution_ref`, the workflow id. A per-run attribute would index nothing that is a Temporal execution of its own.
- **The parent's give-up bound is unchanged.** It already multiplies by the number of operations.

### Persistence, ports and API

- **`table_maintenance_runs` columns (decided: the columns that are queried or sorted on are real columns, the nested data is JSON):**
  - real columns: `id`, `table_uuid`, `execution_ref`, `trigger`, `operation`, `priority`, `status`, `error`, `skip_reason`, `created_at`, `finished_at`;
  - JSON: `filters_json`, `procedure_args_json`, `metrics_json`, `attempts_json`;
  - `operations_json` is dropped. The index stays `(table_uuid, created_at)`.
- **Listing order (decided).** The runs a plan created share one `created_at`. A table's runs list newest first:
  1. `created_at desc`;
  2. then the operation's position in `MaintenanceOperation.ordered()`, descending (a SQLAlchemy `case()`), so the last run of a plan lists first;
  3. then `id desc`.

  The in-memory fake orders the same way.
- **The submit reads its parameters from the run (decided: one source of truth; at HEAD the submit payload carried a second copy of them).**
  - `SubmitMaintenanceOperationUseCaseInput` drops `filters` and `procedure_args`.
  - The service builds the job's `where` list and arguments from `run.filters` and `run.procedure_args`, with the rule at HEAD: `where=[] if not all(wheres) else wheres`.
- **Activity inputs keep `operation` (decided: the Spark job name and the pod labels are built from `(run_id, operation, attempt)`).** Submit, record result, record running, delete job, job status and job pods all check that it equals `run.operation` and raise `ConflictError` otherwise.
- **The callback route becomes `POST /v1/table-maintenance-runs/{run_id}/result` (decided).** The run names its operation, so the path no longer needs to. GitHub updates a check run by its own id (`PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}`) in the same way.
  - `ProcessTableMaintenanceCallbackUseCaseInput.operation` becomes `str | None = None`. The service refuses one that differs from the run's with `ValidationError`, which is 422, the status a body/path mismatch has at HEAD.
  - The Spark runtime does not change: it posts to the `callback_url` it is given, and the submit service builds that url.
- **`TableMaintenanceRunApiResponse` is flat:** `run_id`, `table_uuid`, `execution_ref`, `trigger`, `priority`, `operation`, `status`, `filters`, `procedure_args`, `metrics`, `error`, `skip_reason`, `created_at`, `started_at`, `finished_at`, `attempts`.
  - `attempts: list[TableMaintenanceRunAttemptApiResponse]` is the timeline, and each attempt gains `job_name`.
  - `TableMaintenanceRunOperationApiResponse` is deleted.

### The reconciliation link

- **A reconciliation operation keeps the id of the run it started (decided: one run per operation).**
  - `OperationOutcome.run_id: TableMaintenanceRunId | None` is set exactly when `result` is `STARTED`.
  - No two operations of a record share a run id.
  - The record-level `TableReconciliation.run_id`, its SQL column and its DTO field are removed.
- **`RecordTableReconciliationUseCaseInput.run_ids: dict[str, str]`** (operation → run id) replaces `run_id`, and `run_start_failed` stays.
  - When the child started, the parent sends every planned operation's run id. When it did not start, it sends `{}`.
  - A key that is not a planned operation is a `ValidationError`.
- **`GET /v1/table-reconciliations/{reconciliation_id}` (decided).** A shared link to a record older than the loaded pages must open, as a run's does.

### The console

- **Side panel (user):** `Drawer` with `modal={false}` at 768px and wider. There is no scrim, the list stays usable, and pressing another row shows that record in the same panel. Below 768px it is modal and full width ("the panel becomes a full page").
  - The panel holds a `Timeline` or a `DescriptionList`, never a table.
- **Keyboard (KCL-70):**
  - Enter on a row opens the panel and moves focus to its heading.
  - Pressing another row while the panel is open moves focus to the heading again.
  - Escape or Close returns focus to the row that opened the record now shown.
  - A non-modal panel does not trap focus.
- **Url (user: the url carries the record's id).** Each tab keeps its open record in a search parameter:
  - Maintenance: `?run=<mr-id>`, the parameter name at HEAD, so every old deep link (`../maintenance?run=`) opens the panel;
  - Reconciliations: `?reconciliation=<rc-id>`;
  - Commits: `?snapshot=<snapshot id>`, next to the filters `since`, `until` and `writer`.
  - Opening, switching and closing use `replace` navigation **(decided: the house rule for url state, as for the Tables status filter and the Schema versions; Back leaves the tab instead of stepping through every record opened)**.
- **Where the panel's record comes from (decided).** The panel shows the record from the loaded list when it is there, so it refreshes with the list's 15 s in-flight polling. Otherwise it reads the record by id: `useGetTableMaintenanceRun` or `useGetTableReconciliation`.
  - This closes the known follow-up "the Maintenance tab loads only the latest 50 runs".
  - A 404 reads "This run is no longer available" or "This reconciliation is no longer available".
  - A record of another table reads "This run belongs to another table" or "This reconciliation belongs to another table".
- **Commits read the loaded history only (decided: the commits API has no read by id, and a snapshot outside the filters is the case to explain).** A missing snapshot reads "This commit is not in the history shown. It may be outside the filters, or expired."
- **The design system first (user, `src/data-platform/frontend/CLAUDE.md`):**
  - `Drawer` side-panel mode, `DataTable` rows that open in a panel and `DescriptionList` are built in the design system, with stories and keyboard tests, before any console use.
  - `Timeline` and `TimelineItem` already exist and are reused.
  - `DescriptionList` takes the plain name, since Serendie has no such component. Moving the four hand-rolled fact lists (`CatalogDetails`, `PolicySummary`, `OverviewTab`'s `Fact`, `PlatformSettingsPage`'s `Fact`) onto it is a follow-up.

### Commits and gates

- **No migration (user).** The cluster is rebuilt in the batched verification.
- **Tasks 3 to 8 land as one commit.** The domain change breaks every layer at once, and `contract-test` (regenerated `openapi.json` and client) and `tsc` gate every commit, so the backend, the regenerated client and the console that compiles against it must land together. Tasks 3 to 7 end with "do not commit yet"; Task 8 runs the gate and commits.
- **Task 9 changes the API (a new route) and the console in one commit**, for the same reason.
- Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. `git add` names explicit paths, and no hook is skipped.

## Review Focus

- **Order and one at a time (Task 6).** Every create comes before the first submit. Run 2's first submit comes after run 1's last record and its job deletes, and a failed run 1 still lets run 2 run. The test reads the order from the workflow history (`Harness.commands()`), not from the call lists.
- **Nothing is left pending (Task 6).** A cancel during run 1, a create failure and a submit failure that ends the workflow each leave every later run `skipped`, with the reason. A skip retried after it landed does not fail.
- **Results go to their run (Task 6).** A result naming run 2's id for run 1's operation is dropped. A result for run 2 that arrives while run 1 is running is not taken by run 1.
- **A raise reaches the pending runs (Task 6).** A raise during run 1 of three raises all three. Only run 1's queued attempt is requeued, and a failed raise of run 3 is reported as unapplied.
- **The reconciliation link (Tasks 5 and 6).** A `STARTED` operation has a run id and no other result has one. Ids do not repeat. The parent records `{operation: run_id}` from the same ids it gave the child.
- **Tie order (Task 4).** Runs created in one `now` list newest operation first, in the SQL repo and in the fake.
- **Focus (Tasks 1, 2 and 8).** The panel takes focus on open. Switching rows moves focus to the heading again, and closing returns it to the row last used to open. The list stays clickable at 768px and wider, and below that the panel is modal and full width.
- **Deep links (Tasks 8 and 9).** `?run=` for a run outside the latest 50 opens through the read by id. A 404 or another table's record shows its message inside the panel, never an error banner over the tab.

---

## File Structure

Paths and abbreviations:
- Backend paths are relative to `src/data-platform/backend/`.
- `TM` = `context/table_maintenance`; `TEMPORAL` = `TM/adapter/hybrid/temporal`; `RUN` = `TM/application/domain/model/table_maintenance_run`.
- Tests mirror under `tests/`.
- `DS` = `src/design-system/src`; `FE` = `src/data-platform/frontend/src`.

| File | Responsibility |
|---|---|
| `DS/components/Drawer/{Drawer.tsx,Drawer.stories.tsx}`, `DS/lib/{useMatchesMedia.ts (new),useReturnFocus.ts}` | the non-modal side panel, full width below 768px |
| `DS/components/DataTable/{DataTable.tsx,DataTable.stories.tsx}` | a row that opens in a panel |
| `DS/components/DescriptionList/{DescriptionList.tsx,DescriptionList.stories.tsx}` (new), `DS/index.ts` | a field list for panels |
| `RUN/{table_maintenance_run,operation_attempt,run_status}.py`, `RUN/__init__.py`; deleted: `RUN/operation_run.py`, `RUN/operation_run_status.py` | one run, one operation, one status |
| `TM/adapter/outbound/table_maintenance_run/sql/{table_maintenance_runs_table,table_maintenance_run_row_mapper,table_maintenance_runs_sql_repo}.py`, `tests/.../fakes/in_memory_table_maintenance_runs_repo.py` | storage and listing order |
| `TM/application/port/inbound/table_maintenance_run/*`, new `skip_table_maintenance_run/`; `TM/application/service/table_maintenance_run/*`, new `skip_table_maintenance_run.py`; `TM/application/port/outbound/table_maintenance_run/__init__.py` | run use cases |
| `RUN/../table_reconciliation/{operation_outcome,table_reconciliation}.py`, `TM/application/service/table_reconciliation/{record_table_reconciliation,list_table_reconciliations,table_reconciliation_output_fields (new),get_table_reconciliation (new)}.py`, the matching ports, `TM/adapter/outbound/table_reconciliation/sql/*` | per-operation run links, read by id |
| `TEMPORAL/contracts/table_maintenance/{workflow_input,activity}.py`, `TEMPORAL/inbound/workflows/{table_maintenance_workflow,table_reconciliation_workflow}.py`, `TEMPORAL/contracts/table_reconciliation/*` (the parent's input), `TEMPORAL/inbound/activities/table_maintenance_activities.py` | N runs in order |
| `bootstrap/container/{use_cases,build_use_cases,activities,build_activities}.py`, `TM/adapter/inbound/web/shared/web_use_cases.py` | wiring |
| `TM/adapter/inbound/web/table_maintenance_run/{dto,router}.py`, `TM/adapter/inbound/web/table_reconciliation/{dto,router}.py`, `openapi.json`, `FE/api/generated` | API |
| `FE/components/tabs/{MaintenanceTab,ReconciliationsTab,CommitsTab}.tsx`, `FE/components/tabs/{MaintenanceRunPanel,ReconciliationPanel,CommitPanel}.tsx` (new), `FE/components/tabs/useOpenRecord.ts` (new), `FE/lib/{anyRunInFlight,compactionScopeText}.ts`, `FE/stories/{storyData,lakehouseHandlers}.ts`, `FE/pages/TablePage.stories.tsx` | console |
| `platform/25-lakehouse-control-plane/{e2e.sh,README.md}`, the three `CLAUDE.md`, `docs/agents/{known-follow-ups,project-history}.md` | e2e and docs |

---

### Task 1: The drawer becomes a side panel

Design system only. Commit on its own.

**Files:**
- Create:
  - `DS/lib/useMatchesMedia.ts`, the hook `useMatchesMedia(query: string): boolean`. It reads `window.matchMedia(query)` and follows its `change` events, and on the server it returns `true` (expanded).
  - `DS/lib/useMatchesMedia.test.ts`.
- Modify:
  - `DS/components/Drawer/Drawer.tsx` and `Drawer.stories.tsx`;
  - `DS/lib/useReturnFocus.ts`, which gains `remember()`.
- Test: `useMatchesMedia.test.ts` and the new Drawer stories.

**Interfaces:**
- Consumes (at HEAD): Radix `Dialog` (`modal` prop on `Dialog.Root`), `useReturnFocus(isOpen)` with `focusBeforeOpening()`, and the stories helpers `exerciseOverlay`, `portalQueries` and `expectNoHorizontalPageScroll` from `DS/stories/assertions.ts`.
- Produces: `DrawerProps` gains two props.

```ts
/**
 * false: a side panel beside the page. No scrim, a press outside does not close it, focus is not
 * trapped, and opening moves focus to its heading. Below 768px it is modal and full width anyway.
 */
modal?: boolean; // default true: the drawer at HEAD, unchanged
/**
 * Names the record the panel shows. When it changes while open, focus moves to the heading and
 * the element focused (or pressed) just before becomes the element focus returns to on close.
 */
contentKey?: string;
```

- **The modal case is the drawer at HEAD, unchanged (decided):** it keeps `max-w-sm`, the scrim and the focus on its first control.
- **Non-modal at 768px and wider:**
  - `Dialog.Root modal={false}`, with no `Dialog.Overlay`;
  - `onInteractOutside={(e) => e.preventDefault()}`, so pressing the next row does not close and reopen the panel;
  - `onOpenAutoFocus` prevents the default and focuses the heading. The heading gets `tabIndex={-1}`;
  - classes `w-full md:max-w-sm`, with `border-l border-outline` on the right side (`border-r` on the left). With no scrim, the edge needs a line, and the token is a semantic one.
- **Below 768px** (`useMatchesMedia("(min-width: 48rem)")` false), `modal={false}` acts as `modal` but stays `w-full`. That is the full page.
- **Escape still closes the panel when focus is in the list**, because Radix listens on the document.
- `useReturnFocus` gains `remember(): void`. It stores `focusBeforeOpening()` as the return target when that element is outside the drawer's content. The Drawer calls it, in a layout effect, when `contentKey` changes while open, and then focuses the heading.

- [ ] **Step 1: Write the failing tests and stories**

```ts
// useMatchesMedia.test.ts
it("follows the media query", () => {
  const mql = fakeMediaQueryList(false); // the file's own helper: matches, addEventListener, a `fire(matches)` method
  vi.spyOn(window, "matchMedia").mockReturnValue(mql);
  const { result } = renderHook(() => useMatchesMedia("(min-width: 48rem)"));
  expect(result.current).toBe(false);
  act(() => mql.fire(true));
  expect(result.current).toBe(true);
});
```

Stories in `Drawer.stories.tsx`, each run as a browser test with axe:
- `SidePanel`: a page with an "Open" button, an "Other" button and a non-modal drawer.
  - Its play opens the panel with the keyboard (Tab to "Open", Enter), then expects the panel's heading to have focus.
  - It clicks "Other" and expects the panel still open, "Other" pressed (its counter reads 1) and no element with the `bg-scrim` class in the portal.
  - It presses Escape and expects focus on "Open".
- `SidePanelSwitch`: rows "Row A" and "Row B" each open the panel with `contentKey` set to their name and the title "Record A" or "Record B".
  - Its play presses Row A with Enter, then clicks Row B. It expects the heading "Record B" to have focus.
  - Then it presses Escape and expects focus on "Row B".
- `SidePanelPhone` (`globals: PHONE`): the same panel, opened.
  - The panel's width equals `window.innerWidth`.
  - A scrim is present and focus is trapped: Tab from the last control lands on the first.
  - `expectNoHorizontalPageScroll` passes.
- The existing stories (`Right`, `Left`, `HiddenTitle`, `RightEdge`, `LeftEdge`, `Phone`, `PointerOpened`) stay unchanged and keep passing.

- [ ] **Step 2: Run and watch them fail:** `<ds-vitest> useMatchesMedia`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system run test:stories -- Drawer`. Expected: FAIL; `useMatchesMedia` cannot be imported, and `SidePanel` finds a scrim and focus on the Close button.
- [ ] **Step 3: Implement** as in Interfaces. Export `useMatchesMedia` from `DS/index.ts`, since the console may need the same split later. Add one line to the Drawer's docs story text: "Pass `modal={false}` for a side panel next to a list".
- [ ] **Step 4: Run and watch them pass:** the same two commands.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`; commit `feat(design-system): open the drawer as a side panel beside the page (KCL-95)`.

### Task 2: Table rows that open in a panel, and a description list

Design system only. Commit on its own.

**Files:**
- Create: `DS/components/DescriptionList/DescriptionList.tsx` and `DescriptionList.stories.tsx`, exported with their types from `DS/index.ts`.
- Modify: `DS/components/DataTable/DataTable.tsx` and `DataTable.stories.tsx`; `src/design-system/CLAUDE.md` (add `DescriptionList` to the plain names).
- Test: the new stories.

**Interfaces:**
- `DataTableProps<T>` gains two props.

```ts
/**
 * Opens a row somewhere else, such as a side panel: a plain click on the row, or its first cell's
 * button, calls it. Not combined with renderDetail.
 */
onOpenRow?: (row: T) => void;
/** The row whose panel is open: its button reads aria-expanded="true" and the row is drawn selected. */
openRowId?: string | null;
```

  - The first cell gets a button, the same `IconChevronRight` as the expand toggle. It has `aria-label="Open <getRowLabel(row)>"`, `aria-haspopup="dialog"` and `aria-expanded={openRowId === id}`.
  - A plain click on the row (`isPlainRowClick`) calls `onOpenRow` too, then moves focus to that row's button, so the return target is the row.
  - The open row has `bg-inverse-primary`, the colour rule for selected rows.
  - Passing both `renderDetail` and `onOpenRow` throws in development: a row either expands or opens.
- `DescriptionList({ items, className }: DescriptionListProps)`, where `DescriptionListItem = { term: string; description: ReactNode; id?: string }`.
  - It renders `<dl>` as a grid, `grid-cols-[minmax(0,max-content)_minmax(0,1fr)]` with `gap-x-4 gap-y-2`.
  - `<dt>` is `type-label-medium text-on-surface-variant`, and `<dd>` is `type-body-medium text-on-surface min-w-0 break-words`.
  - Below 768px each pair stacks (term above description), so a long value never forces a horizontal scroll.
  - It is not interactive: a description may hold a link, and the list adds nothing to it.

- [ ] **Step 1: Write the failing stories**
  - `DataTable.stories.tsx` → `OpenRowInPanel`: three rows, `onOpenRow` setting `openRowId`, and a `Drawer modal={false}` showing the open row.
    - Its play tabs to the first row's "Open" button and presses Enter. It expects `aria-expanded="true"` on that button, and the panel heading to have focus.
    - It clicks row 2's name cell. It expects row 2's button to be expanded and row 1's not.
    - It presses Escape and expects focus on row 2's "Open" button.
  - `DescriptionList.stories.tsx`:
    - `Default`: five pairs, one holding a `TextLink`.
    - `LongValues`: one `where` clause of 400 characters with no spaces. It expects the list's `scrollWidth` to be at most its `clientWidth`.
    - `Phone` (`globals: PHONE`): each `dt` sits above its `dd` (`dd.getBoundingClientRect().top >= dt.getBoundingClientRect().bottom`), and `expectNoHorizontalPageScroll` passes.
- [ ] **Step 2: Run and watch them fail:** `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system run test:stories -- DataTable DescriptionList`. Expected: FAIL; `onOpenRow` is not a prop, and `DescriptionList` cannot be imported.
- [ ] **Step 3: Implement** as in Interfaces.
- [ ] **Step 4: Run and watch them pass**, with `<ds-vitest>`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`; commit `feat(design-system): open table rows in a side panel and add a description list (KCL-95)`.

### Task 3: One run, one operation, one status

Domain only. **Do not commit yet** (Tasks 3 to 8 land together).

**Files:**
- Modify: `RUN/table_maintenance_run.py`, `RUN/operation_attempt.py`, `RUN/run_status.py` and `RUN/__init__.py`.
- Delete: `RUN/operation_run.py` and `RUN/operation_run_status.py`, and their test `tests/.../domain/model/table_maintenance_run/test_operation_run.py`. Its nine tests move: the attempt-history checks to `test_table_maintenance_run.py`, the rest are rewritten against the run.
- Test: `tests/context/table_maintenance/application/domain/model/table_maintenance_run/test_table_maintenance_run.py`.

**Interfaces:**
- Consumes (at HEAD): `SpecFilter`, `MaintenanceOperation`, `TablePriority`, `ComputeSize`, `FailureClass`, `NextAttempt`, `NextStep`, and `InvalidRunTransition`.
- Produces:
  - `RunStatus(StrEnum)`: `PENDING`, `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `SKIPPED`.
  - `OperationAttempt` gains `job_name: str | None = None`. Its `status` is a `RunStatus`, with a validator that refuses `PENDING` and `SKIPPED` (`InvariantViolation` "an attempt is queued, running, succeeded or failed").
  - `TableMaintenanceRun` has the fields of Global Constraints and these validators:
    - attempt numbers increase and start at 1 (moved from `OperationRun`);
    - `filters` is non-empty only for `REWRITE_DATA_FILES`;
    - `skip_reason` is set exactly when `status is SKIPPED`;
    - `finished_at` is set exactly when the status is terminal.
  - `TableMaintenanceRun.create(id, table_uuid, trigger, operation: MaintenanceOperation, now, *, execution_ref, priority=TablePriority.P3, filters: Sequence[SpecFilter] = (), procedure_args: Mapping[str, Any] | None = None)`.
  - The methods lose their `operation` parameter:
    - `start_attempt(attempt, job_name, now, *, size)` sets `QUEUED`, and from the first attempt on gives `started_at`;
    - `attach_job_name(attempt, job_name)` writes the attempt's `job_name`;
    - `record_attempt_running(attempt, started_running_at, now)` sets `RUNNING`;
    - `succeed(attempt, metrics, now, *, started_running_at, event_log_finished)`;
    - `fail(attempt, error, now, *, failure_class, started_running_at, event_log_finished, next_attempt)` sets `FAILED` and `finished_at`. The next `start_attempt` clears `finished_at` and sets `QUEUED`, as the operation at HEAD did;
    - `attempt_record(attempt)`;
    - `raise_priority(priority) -> bool`, unchanged: upward only, never once finished;
    - `skip(reason, now)`: pending only, else `InvalidRunTransition`.
  - `@property started_at -> datetime | None`.

- [ ] **Step 1: Write the failing tests.** Rewrite the helpers at the top of `test_table_maintenance_run.py`:
  - `_run(ops)` becomes `_run(operation: Op = Op.EXPIRE_SNAPSHOTS, **create_kwargs)`;
  - `_op` is deleted;
  - `_run_with_filters` becomes `_run(Op.REWRITE_DATA_FILES, filters=[EU])`.

  Keep `RUN_1`, `T0`, `_now` and `EU`. Then adapt the 57 tests at HEAD: each one names its operation once, through `_run(...)`, instead of on every method call. Add:

```python
COMPACTION = Op.REWRITE_DATA_FILES
STOPPED = "the table's maintenance stopped before this run started"


def test_a_new_run_is_pending_with_no_attempt():
    run = _run()
    assert (run.operation, run.status, run.attempts, run.started_at, run.finished_at) == (
        Op.EXPIRE_SNAPSHOTS, RunStatus.PENDING, (), None, None,
    )


def test_the_first_attempt_queues_and_starts_the_run():
    run = _run()
    run.start_attempt(1, "tm-es-x-a1", _now(1), size=ComputeSize.S)
    assert (run.status, run.started_at) == (RunStatus.QUEUED, _now(1))
    assert (run.attempts[0].status, run.attempts[0].job_name) == (RunStatus.QUEUED, "tm-es-x-a1")


def test_each_attempt_keeps_its_own_job_name():
    run = _run()
    run.start_attempt(1, "job-a1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), failure_class=FailureClass.OTHER, started_running_at=_now(1),
             event_log_finished=None, next_attempt=NextAttempt(step=NextStep.RETRY_SAME, size=ComputeSize.S))
    run.start_attempt(2, "job-a2", _now(3), size=ComputeSize.S)
    assert [a.job_name for a in run.attempts] == ["job-a1", "job-a2"]
    assert run.started_at == _now(1)


def test_success_finishes_the_run_with_the_procedure_numbers():
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.succeed(1, {"deleted_data_files_count": 3}, _now(5), started_running_at=_now(2), event_log_finished=True)
    assert (run.status, run.metrics, run.finished_at, run.error) == (
        RunStatus.SUCCEEDED, {"deleted_data_files_count": 3}, _now(5), None,
    )


def test_a_failure_with_a_retry_reads_failed_until_the_next_attempt():  # known follow-up, pinned
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), failure_class=FailureClass.OTHER, started_running_at=None,
             event_log_finished=None, next_attempt=NextAttempt(step=NextStep.RETRY_SAME, size=ComputeSize.S))
    assert run.status is RunStatus.FAILED
    run.start_attempt(2, None, _now(3), size=ComputeSize.S)
    assert (run.status, run.finished_at) == (RunStatus.QUEUED, None)


def test_a_pending_run_is_skipped_with_its_reason():
    run = _run()
    run.skip(STOPPED, _now(1))
    assert (run.status, run.skip_reason, run.error, run.finished_at) == (RunStatus.SKIPPED, STOPPED, None, _now(1))


def test_a_started_run_cannot_be_skipped():
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.skip(STOPPED, _now(2))


def test_a_run_keeps_the_parameters_it_passes():
    run = _run(procedure_args={"older_than": "2026-10-23T00:00:00+00:00", "retain_last": 1})
    assert run.procedure_args == {"older_than": "2026-10-23T00:00:00+00:00", "retain_last": 1}


def test_a_compaction_run_keeps_its_filters():
    assert _run(COMPACTION, filters=[EU]).filters == (EU,)


def test_filters_on_another_operation_are_refused():
    with pytest.raises(InvalidRunTransition):
        _run(Op.EXPIRE_SNAPSHOTS, filters=[EU])


@pytest.mark.parametrize("status", [RunStatus.PENDING, RunStatus.SKIPPED])
def test_an_attempt_is_never_pending_or_skipped(status):
    with pytest.raises(InvariantViolation, match="queued, running, succeeded or failed"):
        OperationAttempt(attempt=1, size=ComputeSize.S, status=status, started_at=_now())


def test_there_is_no_partially_failed_status():
    assert {s.value for s in RunStatus} == {"pending", "queued", "running", "succeeded", "failed", "skipped"}
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table_maintenance_run -v`. Expected: FAIL; `create` takes a list of operations, and `skip` wants an operation.
- [ ] **Step 3: Implement.** Move `OperationRun`'s validator and its per-attempt helpers onto the run. Delete the two files and the test file, and update `RUN/__init__.py` (drop `OperationRun` and `OperationRunStatus`). `grep -rn "OperationRun\b\|OperationRunStatus\|PARTIALLY_FAILED" src/data-platform/backend` lists what Tasks 4 to 7 change.
- [ ] **Step 4: Run and watch them pass:** the same command. **Do not commit yet:** the services, the mapper and the workflow do not compile against the new run until Task 7.

### Task 4: Storage and the run use cases

**Do not commit yet.**

**Files:**
- Modify:
  - `TM/adapter/outbound/table_maintenance_run/sql/table_maintenance_runs_table.py`, `table_maintenance_run_row_mapper.py` (delete `_encode_operation` and `_decode_operation`; keep `_encode_attempt` and `_decode_attempt`, with `job_name`) and `table_maintenance_runs_sql_repo.py` (`list_by_table` order);
  - `tests/.../fakes/in_memory_table_maintenance_runs_repo.py` (same order);
  - `TM/application/port/outbound/table_maintenance_run/__init__.py`: re-export `RunStatus` and stop re-exporting `OperationRun` and `OperationRunStatus`;
  - the inbound ports under `TM/application/port/inbound/table_maintenance_run/`: `create_table_maintenance_run`, `get_table_maintenance_run`, `list_table_maintenance_runs`, `submit_maintenance_operation`, `process_table_maintenance_callback`, `record_table_maintenance_operation_result`, `record_maintenance_attempt_running`, `raise_table_maintenance_run_priority`;
  - the services under `TM/application/service/table_maintenance_run/` of the same names, and `table_maintenance_run_output_fields.py`. The job services (`delete_maintenance_job.py`, `get_maintenance_job_status.py`, `get_maintenance_job_pods.py`) gain the operation check.
- Create:
  - `TM/application/port/inbound/table_maintenance_run/skip_table_maintenance_run/{__init__,input,output,use_case}.py` (`raise_table_maintenance_run_priority/` is the pattern);
  - `TM/application/service/table_maintenance_run/skip_table_maintenance_run.py`;
  - wiring in `bootstrap/container/{use_cases,build_use_cases}.py` (`skip_table_maintenance_run=SkipTableMaintenanceRunService(runs)`).
- Test (all under `tests/context/table_maintenance/`):
  - `adapter/outbound/table_maintenance_run/test_table_maintenance_runs_sql_repo.py`;
  - `application/service/table_maintenance_run/test_table_maintenance_run_services.py`, `test_table_maintenance_job_services.py`, `test_record_table_maintenance_operation_result.py`, `test_record_maintenance_attempt_running.py` and `test_raise_table_maintenance_run_priority.py`;
  - `tests/architecture/test_inbound_port_field_types.py` (it must keep passing).

**Interfaces:**
- Consumes: the run of Task 3.
- Produces:
  - `CreateTableMaintenanceRunUseCaseInput`: `run_id`, `table_uuid`, `execution_ref`, `trigger`, `operation: str`, `now`, `priority: str = "P3"`, `filters: tuple[Filter, ...] = ()` (nested `Filter(spec_id, where)`, as at HEAD), `procedure_args: dict[str, Any] = Field(default_factory=dict)`.
    - An unknown operation is a `ValidationError`, raised inside `translate_domain_errors()`.
    - The service is idempotent by run id, and a manual trigger clears needs attention, both as at HEAD.
  - The Create, Get and List outputs carry the flat fields of Global Constraints. `attempts: tuple[dict[str, Any], ...]`, each attempt a dict with `job_name`. The list output's nested `TableMaintenanceRun` class has the same fields. `table_maintenance_run_output_fields(run)` builds them all.
  - `SubmitMaintenanceOperationUseCaseInput`: `run_id`, `operation`, `attempt`, `callback_base_url`, `now`, `size="S"`. It no longer has `filters` or `procedure_args`.
    - The service reads `run.filters` and `run.procedure_args`.
    - The `callback_url` is `{callback_base_url}/v1/table-maintenance-runs/{run_id}/result`.
  - `ProcessTableMaintenanceCallbackUseCaseInput.operation: str | None = None`. The service:
    - raises `NotFoundError` for an unknown run, as at HEAD;
    - raises `ValidationError` "the run's operation is <op>" for another operation;
    - otherwise forwards `operation=run.operation.value`.
  - Every service that takes `run_id` and `operation` raises `ConflictError("run <id> does not run <op>")` when they disagree.
  - `SkipTableMaintenanceRunUseCaseInput(run_id: str, reason: str, now: datetime)` and `SkipTableMaintenanceRunUseCaseOutput(run_id: str, status: str, skipped: bool)`.
    - A pending run is skipped (`skipped=True`). A run in any other status is left alone (`skipped=False`).
    - A missing run is `NotFoundError`.
  - `RecordTableMaintenanceOperationResultUseCaseOutput.status` is the run's status.

- [ ] **Step 1: Write the failing tests.** Adapt the helpers at HEAD:
  - SQL repo: `_run(run_id, table, at)` gains `operation=Op.EXPIRE_SNAPSHOTS`; keep `NOW`, `R1`, `OTHER` and `MISSING`;
  - services: `_create_input(now, run_id=RUN_1, **overrides)` now takes `operation=RDF` in place of `operations=(...)`; keep `_record(recorder, now, **overrides)`, `RUN_1`, `RUN_2` and `UNKNOWN_RUN`.

  Then add:

```python
# test_table_maintenance_runs_sql_repo.py
def test_sql_round_trip_keeps_every_field(repo):
    run = TableMaintenanceRun.create(TableMaintenanceRunId(R1), TableId("u1"), TriggerType.SCHEDULED,
                                     Op.REWRITE_DATA_FILES, NOW, execution_ref="wf",
                                     filters=[SpecFilter(spec_id=0, where="(`region` = 'eu')")],
                                     procedure_args={"options": {"min-input-files": "2"}})
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    run.succeed(1, {"rewritten_data_files_count": 4}, NOW, started_running_at=NOW, event_log_finished=True)
    repo.create(run)
    assert repo.get(TableMaintenanceRunId(R1)) == run


def test_runs_created_together_list_the_last_operation_first(repo):
    ops = [Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS, Op.REMOVE_ORPHAN_FILES]
    for n, op in enumerate(ops, start=1):
        repo.create(_run(numbered_id("mr", n), operation=op))
    listed = repo.list_by_table(TableId("u1"))
    assert [r.operation for r in listed] == list(reversed(ops))


def test_the_status_is_a_column(repo, engine):
    repo.create(_run(R1))
    with engine.connect() as conn:
        assert conn.execute(text("select status, operation from table_maintenance_runs")).one() == ("pending", "expire_snapshots")


# test_table_maintenance_run_services.py
def test_create_saves_one_operation_with_its_parameters(): ...
    # _create_input(now, operation="expire_snapshots", procedure_args={"retain_last": 1})
    # → runs_repo.get(RUN_1): operation EXPIRE_SNAPSHOTS, procedure_args {"retain_last": 1}, status PENDING
def test_create_refuses_an_unknown_operation(): ...       # operation="compact" → ValidationError, nothing stored
def test_create_refuses_filters_on_expire(): ...          # operation="expire_snapshots", filters=(Filter(0, "x"),) → ValidationError
def test_list_shows_runs_created_together_last_operation_first(): ...  # the fake, two runs at one now → second operation first
def test_skip_skips_a_pending_run(): ...                  # → status "skipped", skipped True, skip_reason stored
def test_skip_leaves_a_started_run_alone(): ...           # start_attempt first → skipped False, status "queued"
def test_skip_of_an_unknown_run_is_not_found(): ...       # UNKNOWN_RUN → NotFoundError


# test_table_maintenance_job_services.py
def test_submit_takes_the_where_and_the_arguments_from_the_run(): ...
    # run created with filters [EU] and procedure_args {"options": {"min-input-files": "2"}}; the submit input has neither
    # → RecordingSubmitMaintenanceJobGateway.calls[0] carries where ["(`region` = 'eu')"] and those arguments
def test_submit_builds_the_run_result_callback_url(): ...  # the assert at HEAD (line 138) → ".../v1/table-maintenance-runs/{RUN_1}/result"
def test_submit_refuses_another_operation(): ...          # run of expire_snapshots, operation "rewrite_data_files" → ConflictError, no submit
def test_callback_forwards_the_runs_operation_when_the_body_names_none(): ...  # operation None → gateway input operation "expire_snapshots"
def test_callback_refuses_another_operation(): ...        # operation "rewrite_data_files" → ValidationError, nothing sent
```

The `...` bodies copy the arrange part of the neighbouring tests in the same file, and assert what follows the arrow. In `test_record_table_maintenance_operation_result.py`, `test_record_maintenance_attempt_running.py` and `test_raise_table_maintenance_run_priority.py`, each test builds a run with one operation, and the "operation not in run" tests become "another operation is a ConflictError".

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/outbound/table_maintenance_run tests/context/table_maintenance/application/service/table_maintenance_run -v`.
- [ ] **Step 3: Implement.**
  - The repo's order is `order_by(created_at.desc(), case({op.value: i for i, op in enumerate(MaintenanceOperation.ordered())}, value=operation).desc(), id.desc())`. The fake sorts by the same key.
  - `record_table_maintenance_operation_result.py` keeps `_already_recorded`, the evidence reads, classify and decide-next, but against the run. It keeps recording on the table (`RecordedAttempt`) and the needs-attention mark.
- [ ] **Step 4: Run and watch them pass:** the same command, plus `<pytest> tests/architecture -q`. **Do not commit yet.**

### Task 5: Each reconciliation operation links its own run

**Do not commit yet.**

**Files:**
- Modify:
  - `TM/application/domain/model/table_reconciliation/operation_outcome.py` and `table_reconciliation.py`;
  - `TM/application/port/inbound/table_reconciliation/record_table_reconciliation/input.py` and `list_table_reconciliations/output.py`;
  - `TM/application/service/table_reconciliation/record_table_reconciliation.py` and `list_table_reconciliations.py`;
  - `TM/adapter/outbound/table_reconciliation/sql/table_reconciliations_table.py` (drop the `run_id` column) and `table_reconciliation_row_mapper.py`;
  - `TM/adapter/inbound/web/table_reconciliation/dto.py`.
- Test:
  - `tests/.../domain/model/table_reconciliation/test_table_reconciliation.py` (the file holding the run-id validator tests at HEAD);
  - `tests/.../service/table_reconciliation/test_record_table_reconciliation_service.py` and `test_list_table_reconciliations_service.py`;
  - `tests/.../adapter/outbound/table_reconciliation/test_table_reconciliations_sql_repo.py`;
  - `tests/.../adapter/inbound/web/table_reconciliation/test_table_reconciliation_routes.py`.

**Interfaces:**
- Produces:
  - `OperationOutcome.run_id: TableMaintenanceRunId | None = None`. The validator raises `InvariantViolation` when:
    - `run_id` is set and `result` is not `STARTED`: "only a started operation has a run";
    - `result` is `STARTED` and `run_id` is `None`: "a started operation names its run".
  - `TableReconciliation` loses `run_id`. Its validator refuses two operations with the same `run_id` ("each run belongs to one operation").
  - `RecordTableReconciliationUseCaseInput.run_ids: dict[str, str] = Field(default_factory=dict)` replaces `run_id`. In the service, `_result` gives `STARTED` when the operation is in `run_ids`, then `START_FAILED` when `run_start_failed`, then `WOULD_START` on a dry run, as at HEAD. A key that is not a planned operation is a `ValidationError`.
  - `ListTableReconciliationsUseCaseOutput.Operation.run_id: str | None`. `TableReconciliation.run_id` is removed.
  - `ReconciliationOperationApiResponse.run_id: str | None = Field(description="The mr- id of the maintenance run this operation started; set only when result is started.")`. `TableReconciliationApiResponse.run_id` is removed.
  - The `operations_json` entry gains `"run_id"`. A missing key reads as `None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_started_operation_names_its_run(): ...         # OperationOutcome(result=STARTED, run_id=None) → InvariantViolation "names its run"
def test_only_a_started_operation_has_a_run(): ...        # result NOT_NEEDED, run_id=mr-1 → InvariantViolation
def test_two_operations_cannot_share_a_run(): ...         # two STARTED outcomes, same run id → InvariantViolation
def test_record_links_each_started_operation_to_its_run(): ...
    # run_ids {"rewrite_data_files": R1, "expire_snapshots": R2} with both planned
    # → stored outcomes: rewrite STARTED run R1, expire STARTED run R2; the other operations run None
def test_record_refuses_a_run_for_an_operation_not_planned(): ...  # run_ids {"rewrite_manifests": R1}, not planned → ValidationError
def test_a_start_failure_links_no_run(): ...              # run_ids {}, run_start_failed True → START_FAILED, run None
def test_sql_round_trip_keeps_each_operations_run(): ...  # the record above → get(...) equal
def test_list_shows_the_run_of_each_operation(): ...      # output.items[0].operations[i].run_id
def test_the_api_shows_the_run_on_each_operation(client): ...  # body[0]["operations"][i]["run_id"]; "run_id" not in body[0]
```

The `...` bodies follow the same rule as in Task 4.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "reconciliation" -v`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass.** **Do not commit yet:** the parent workflow still sends `run_id` until Task 6.

### Task 6: The table's workflow runs one run per operation, in order

**Do not commit yet.**

**Files:**
- Modify:
  - `TEMPORAL/contracts/table_maintenance/workflow_input.py` (`run_ids`);
  - `TEMPORAL/contracts/table_maintenance/activity.py` (`SKIP_MAINTENANCE_RUN = "skip_maintenance_run"`);
  - the parent's input contract `TableReconciliationWorkflowInput` under `TEMPORAL/contracts/table_reconciliation/` (`in_flight_run_ids`);
  - `TEMPORAL/inbound/workflows/table_maintenance_workflow.py` and `table_reconciliation_workflow.py`;
  - `TEMPORAL/inbound/activities/table_maintenance_activities.py` (a `skip_table_maintenance_run` activity, wired in `bootstrap/container/{activities,build_activities}.py`).
- Test (all under `tests/context/table_maintenance/adapter/hybrid/temporal/`):
  - `inbound/test_table_maintenance_workflow.py`, `inbound/scripted_maintenance_activities.py`, `inbound/table_maintenance_stub_workflow.py`, `inbound/test_table_reconciliation_workflow.py`, `inbound/test_run_activity_payloads.py`, `inbound/test_activities.py`, `inbound/use_case_fakes.py`;
  - `contracts/test_wire_names.py`;
  - `tests/architecture/test_temporal_workflow_determinism.py`, which must keep passing.

**Interfaces:**
- Consumes: the use cases of Task 4 (create with one operation, skip) and the record input of Task 5 (`run_ids`).
- Produces:
  - `TableMaintenanceWorkflowInput(run_ids: list[str], table_uuid, parent_workflow_id, trigger, plan, attempt_deadline_seconds, max_attempts, queue_wait_limit_seconds)`.
  - **Child.** `self._run_of: dict[str, str]` maps each operation to its run id, built with `zip(..., strict=True)`. `run()` then:
    1. for each operation, calls `CREATE_MAINTENANCE_RUN` with `{"run_id", "table_uuid", "execution_ref", "trigger", "operation", "priority", "filters": op["filters"], "procedure_args": op["procedure_args"], "now"}`, all with the same `now`;
    2. for each operation: `_run_operation(op)`, then deletes that run's started jobs (`_delete_jobs_of(op)`);
    3. in `finally`, `_finish`: it deletes the started jobs still left, skips every run not started (`{"run_id", "reason": "the table's maintenance stopped before this run started", "now"}`, a failure logged as a warning), and then signals the parent.
  - Every activity payload's `run_id` is `self._run_of[operation]`. The submit payload loses `filters` and `procedure_args`.
  - `operation_result` keeps a signal only when `self._run_of.get(result.operation) == result.run_id`.
  - `_apply_raises` calls `RAISE_MAINTENANCE_RUN_PRIORITY` for the current run and then each later run that has not started. The current run's reply decides the requeue, and any `ActivityError` sets `_dropped_raise`.
  - The report is `{"run_ids": [...], "record_failures", "unapplied_raise", "raises_received"}`.
  - **Parent.**
    - `_mint_ids()` returns only the `rc-` id, under its existing patch.
    - After a plan with operations, it mints `run_ids = [mint_workflow_prefixed_id(_RUN_ID_PREFIX) for _ in plan["operations"]]`.
    - `_start_run(plan, manual, run_ids)` sets `self._in_flight_run_ids = run_ids`.
    - `_record(record, plan, *, run_ids: dict[str, str], run_start_failed)` sends `"run_ids"`: `dict(zip(operations, run_ids))` when started, else `{}`.
    - `maintenance_finished` matches `payload.get("run_ids") == self._in_flight_run_ids`.
    - The `state()` query reports `"in_flight_run_ids"`.
  - The stub workflow reports `{"run_ids": input.run_ids, ...}`.

- [ ] **Step 1: Write the failing tests.**
  - In `test_table_maintenance_workflow.py`:
    - `RUN_ID` becomes `RUN_IDS = (numbered_id("mr", 1), numbered_id("mr", 2), numbered_id("mr", 3), numbered_id("mr", 4))`.
    - `Harness.start_maintenance` passes `run_ids=list(RUN_IDS[: len(plan["operations"])])`.
    - `_report(...)` takes `run_ids` (default the first one).
  - In `scripted_maintenance_activities.py`:
    - add `skips: list[dict]`, `create_errors: set[str]` (run ids whose create fails) and a `skip_maintenance_run` activity that records the request and returns `{"run_id": ..., "status": "skipped", "skipped": True}`;
    - `app_name(run_id, operation, attempt)` and `_workflow_id_of(run_id)` stay.

```python
def test_each_operation_gets_its_own_run_created_before_the_first_submit():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)
        assert [(c["run_id"], c["operation"]) for c in h.fakes.created] == [(RUN_IDS[0], COMPACTION), (RUN_IDS[1], EXPIRE)]
        assert h.fakes.created[0]["filters"] == [{"spec_id": 0, "where": f"{COMPACTION} = 1"}]
        assert h.fakes.created[1]["procedure_args"] == {"op": EXPIRE}
        assert "filters" not in h.fakes.submits[0] and "procedure_args" not in h.fakes.submits[0]
        names = [name for name, _ in await h.commands()]
        assert names.index("submit_maintenance_operation") > max(i for i, n in enumerate(names) if n == "create_maintenance_run")
        assert [(s["run_id"], s["operation"]) for s in h.fakes.submits] == [(RUN_IDS[0], COMPACTION), (RUN_IDS[1], EXPIRE)]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]
    _run(scenario)


def test_the_next_run_submits_only_after_the_previous_run_ended():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)
        names = [name for name, _ in await h.commands()]
        second_submit = [i for i, n in enumerate(names) if n == "submit_maintenance_operation"][1]
        assert names.index("record_maintenance_operation_result") < names.index("delete_maintenance_job") < second_submit
    _run(scenario)


def test_a_failed_run_does_not_stop_the_next(): ...
    # COMPACTION fails permanently (record reply next_step "not_retried"); EXPIRE succeeds
    # → h.recorded() ends with (EXPIRE, 1, True, None); no skip
def test_runs_never_reached_are_skipped_when_the_workflow_is_cancelled(): ...
    # three operations, cancel while COMPACTION is blocked (_cancel_while_blocked)
    # → [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1], RUN_IDS[2]], each reason
    #   "the table's maintenance stopped before this run started"; the report still reaches the parent
def test_a_create_failure_submits_nothing_and_skips_the_runs_created(): ...
    # create_errors {RUN_IDS[1]} → submits == []; skips == [RUN_IDS[0]] (RUN_IDS[1] was not created; its skip is logged)
def test_a_result_naming_another_runs_id_is_dropped(): ...
    # while COMPACTION attempt 1 waits, signal OperationResultSignal(run_id=RUN_IDS[1], operation=COMPACTION, attempt=1, ...)
    # → it is not recorded; the real callback for RUN_IDS[0] is
def test_a_raise_reaches_every_run_not_finished(): ...
    # three operations, a raise to P1 while COMPACTION is queued
    # → [r["run_id"] for r in h.fakes.raises] == list(RUN_IDS[:3]); only COMPACTION's attempt is requeued
def test_a_failed_raise_of_a_later_run_is_reported_unapplied(): ...  # raise_errors on the third call → report unapplied_raise True
def test_the_jobs_of_a_run_are_deleted_when_it_ends(): ...  # h.fakes.deletes == [app_name(RUN_IDS[0], COMPACTION, 1), app_name(RUN_IDS[1], EXPIRE, 1)]


# test_table_reconciliation_workflow.py
def test_a_plan_of_three_operations_starts_one_child_with_three_runs(): ...
    # _planned(COMPACTION, EXPIRE, ORPHANS) → the child input's run_ids: three, distinct, each matching RUN_ID_SHAPE;
    # the record activity's run_ids == dict(zip(the three operations, those ids))
def test_a_report_naming_other_runs_is_ignored(): ...     # maintenance_finished {"run_ids": [OTHER_RUN_ID]} → still in flight
def test_the_runs_in_flight_survive_continue_as_new(): ... # the carried input's in_flight_run_ids equals the state before
def test_a_child_that_did_not_start_links_no_run(): ...   # start refused → record run_ids {}, run_start_failed True
```

The `...` bodies follow the same rule as in Task 4.
  - Update the existing tests that name `RUN_ID`, `in_flight_run_id` or `GHOST_RUN_ID`. `start_with_a_gone_child` passes `in_flight_run_ids=[GHOST_RUN_ID]`, and a `state()` assertion reads `in_flight_run_ids`.
  - In `test_wire_names.py`, pin `skip_maintenance_run`.
  - In `test_run_activity_payloads.py` and `test_activities.py`, the create payload has `operation` and `procedure_args`, and the submit payload has neither `filters` nor `procedure_args`.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal -v`. Expected: FAIL; the input has no `run_ids`, and the activity name is unknown.
- [ ] **Step 3: Implement.** Keep the attempt loop, the fences, the requeue, the polls and every existing patch as they are; only the run id each call names changes. The parent's 21 uses of `_in_flight_run_id` become `_in_flight_run_ids`, compared as a whole list.
- [ ] **Step 4: Run and watch them pass:** the same command, then `<pytest> tests/architecture -q`. Run the reconciliation workflow file twice, since it has one known flaky test (`test_give_up_waits_for_a_cancelled_child_that_is_still_running`). **Do not commit yet.**

### Task 7: The run API, the callback route and the client

**Do not commit yet:** the regenerated client breaks the console until Task 8.

**Files:**
- Modify:
  - `TM/adapter/inbound/web/table_maintenance_run/dto.py`: delete `TableMaintenanceRunOperationApiResponse`, flatten `TableMaintenanceRunApiResponse`, add `job_name` to `TableMaintenanceRunAttemptApiResponse`;
  - `TM/adapter/inbound/web/table_maintenance_run/router.py`: the callback path;
  - `openapi.json` and `FE/api/generated` through `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- Test:
  - `tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run/test_table_maintenance_run_routes.py` (`URL` at line 95, the path list at line 361);
  - `tests/architecture/test_dto_naming.py`.

**Interfaces:**
- Produces:
  - `TableMaintenanceRunApiResponse` with the flat fields. The descriptions:
    - `operation`: "The one operation this run does.";
    - `filters`: KCL-94's description;
    - `procedure_args`: "The arguments this run passes to the Iceberg procedure, besides the where clauses.";
    - `metrics`: "The numbers the procedure returned.";
    - `skip_reason`: "Why the run was skipped; set only when status is skipped.";
    - `started_at`: "When the first attempt was submitted; null while pending.";
    - `attempts`: "Every attempt, oldest first.".
  - `POST /v1/table-maintenance-runs/{run_id}/result`. The body (`ProcessTableMaintenanceCallbackApiRequest`, `extra="ignore"`) is unchanged.
    - A body `run_id` other than the path's is 422, as at HEAD.
    - A body `operation` other than the run's is 422 (the service's `ValidationError`).
    - An unknown run is 404.
  - The old path `/v1/table-maintenance-runs/{run_id}/operations/{operation}/result` is gone (404).

- [ ] **Step 1: Write the failing tests:** `URL = f"/v1/table-maintenance-runs/{RUN_ID}/result"`. Keep `RUN_ID`, `CALLBACK`, `EU` and `EU_BODY`; `_stored_run(runs, *, with_filters)` creates a one-operation run.

```python
def test_get_run_is_flat(client): ...                     # body["operation"] == "rewrite_data_files"; "operations" not in body;
                                                          # body["attempts"][0]["job_name"]; body["started_at"]; body["procedure_args"]
def test_a_pending_run_has_no_start(client): ...          # created only → status "pending", started_at None, attempts []
def test_the_callback_needs_no_operation_in_its_path(client): ...  # POST URL with CALLBACK minus "operation" → 202/200 as at HEAD
def test_the_callback_refuses_another_operation(client): ...       # body operation "expire_snapshots" on a compaction run → 422
def test_the_old_callback_path_is_gone(client): ...       # POST .../operations/rewrite_data_files/result → 404
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run -v`.
- [ ] **Step 3: Implement**, then run `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`. The whole backend suite passes from here on. Then run `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend ty check`, `ruff check .` and `lint-imports` the same way. **Do not commit yet.**

### Task 8: The Maintenance tab opens a run in the side panel

Then commit Tasks 3 to 8 together.

**Files:**
- Create:
  - `FE/components/tabs/MaintenanceRunPanel.tsx`: the panel's content;
  - `FE/components/tabs/useOpenRecord.ts`: `useOpenRecord(param: string): { openId: string | null; open(id: string): void; close(): void }`. It reads and writes one search parameter with `replace` and keeps the others. Tasks 9 and 10 reuse it.
  - `FE/components/tabs/useOpenRecord.test.ts`.
- Modify:
  - `FE/components/tabs/MaintenanceTab.tsx` and `MaintenanceTab.test.tsx`;
  - `FE/components/tabs/ReconciliationsTab.tsx` and `ReconciliationsTab.test.tsx`: the run link per operation;
  - `FE/lib/anyRunInFlight.ts` and `anyRunInFlight.test.ts`, which read `run.status` and `run.attempts`;
  - `FE/lib/compactionScopeText.ts` and `compactionScopeText.test.ts`, which take the run;
  - `FE/lib/attemptText.ts` only if a type name changes;
  - `FE/stories/storyData.ts`, with every run fixture flat and every reconciliation fixture carrying `run_id` per operation;
  - `FE/stories/lakehouseHandlers.ts`: a `getGetTableMaintenanceRunMockHandler` answering by id from all fixtures;
  - `FE/pages/TablePage.stories.tsx`;
  - `FE/components/RunMaintenanceDialog.test.tsx`, `RunMaintenanceDialog.stories.tsx` and `TableHeader.test.tsx`, whose run fixtures change shape.
- Test: the files above and `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.

**Interfaces:**
- Consumes:
  - the generated `TableMaintenanceRunApiResponse` (flat), `useListTableMaintenanceRuns` and `useGetTableMaintenanceRun` (Task 7);
  - `Drawer modal={false} contentKey`, `DataTable onOpenRow openRowId` and `DescriptionList` (Tasks 1 and 2);
  - `Timeline`, `TimelineItem` and `StatusBadge`.
- Produces:
  - **The runs list:** one row per run. The columns are Operation (`operationLabel`), Trigger, Status (`RunStatusBadge`), Started (`started_at`, "—" while pending or skipped) and Duration (from `started_at` to `finished_at`).
    - `getRowLabel` gives `` `${operationLabel(run.operation)} run ${run.run_id}` ``, so the row's button reads "Open Compaction run mr-…".
    - `onOpenRow` calls `open(run.run_id)`, and `openRowId={openId}`.
    - `renderDetail`, `initialExpandedRowIds`, the `key={linkedRunId}` remount and the "This run is no longer available" banner over the list are all removed.
  - **The panel:** `Drawer modal={false} contentKey={openId}` with the title `operationLabel(run.operation)`. `MaintenanceRunPanel({ run, now })` holds:
    - a `DescriptionList`:
      - Run (`run_id`, mono), Status (badge), Trigger, Priority;
      - Started, Finished, Duration;
      - Scope (`compactionScopeText`, compaction only, each `spec N: …` on its own line, `break-all`);
      - Parameters (each `procedure_args` key, mono, with its JSON value; omitted when empty);
      - Result (each `metrics` key with its value; omitted when empty);
      - Error (`negative-text`, when set);
      - Skipped (`skip_reason`, when set);
      - Execution (`execution_ref`, mono);
    - a heading "Attempts", then a `Timeline` with one `TimelineItem` per attempt, oldest first:
      - the marker is `filled` when the attempt ended and `outlined` while queued or running;
      - the title is `Attempt {n} · {size}` with a `StatusBadge`;
      - the description is the existing `attemptText` lines: queue wait, run time, failure class, next step, event log, and the job name in mono;
      - a pending run reads "No attempt yet. This run waits for the runs before it." instead of the timeline.
  - **Where the panel's run comes from:** the list's run when it is in the latest 50, else `useGetTableMaintenanceRun(openId, { query: { enabled: notInList } })`.
    - A 404 shows "This run is no longer available" in the panel. A run whose `table_uuid` is another table's shows "This run belongs to another table".
    - While the read by id loads, the panel shows `PanelSkeleton label="Loading run…"`.
  - **Reconciliations:**
    - `OperationBlock` links `operation.run_id`, "Open maintenance run mr-…", to `../maintenance?run=<id>`, the same `runPath`.
    - `RecordLine`'s trailing link shows only when exactly one operation started a run **(decided: a timeline line holds one action, and the panel lists one link per operation)**.
    - `startedRun(r)` is deleted.
  - **Polling:** `anyRunInFlight(runs)` is true when any run's status is in flight (`isInFlightStatus`), or any attempt of it is.

- [ ] **Step 1: Write the failing tests and stories**
  - `useOpenRecord.test.ts`: `open("mr-1")` on `/t?since=x` gives `?since=x&run=mr-1` with `replace`, and `close()` gives `?since=x`.
  - `MaintenanceTab.test.tsx`, its run fixtures flat:
    - the list shows one row per run, with Operation "Compaction";
    - a click on a row's name opens `getByRole("dialog", { name: "Compaction" })`, and the url gains `run=<id>`;
    - the panel lists "Attempt 1 · S" with "Failed" and "Retrying at size M" (`ESCALATED_RUN`), then "Attempt 2 · M" with "Succeeded";
    - the panel shows `Scope` and `spec 0: (`region` = 'eu')` for a compaction, and `Parameters` with `retain_last` for an expire run;
    - a click on another row while the panel is open shows that run, and only one dialog exists;
    - Escape closes the panel, removes `run` from the url and focuses that row's "Open …" button;
    - `?run=<OLDER_RUN_ID>` (not in the list) reads it by id through MSW and opens the panel; the call log holds one `GET /table-maintenance-runs/<id>`;
    - `?run=mr-…missing` answered 404 shows "This run is no longer available" inside the dialog;
    - a run of another table shows "This run belongs to another table";
    - a pending run shows "No attempt yet. This run waits for the runs before it." and Started "—".
  - `anyRunInFlight.test.ts`: a `pending` run is in flight, and a `skipped` one is not.
  - `ReconciliationsTab.test.tsx`:
    - a record whose two operations started two runs shows two "Open maintenance run" links in its panel, each with its own id;
    - its line has no trailing "Run" link;
    - a record with one run keeps the trailing link.
  - `storyData.ts`:
    - `RUNS` becomes the four runs of one plan, all created at `2026-11-08T02:00:00Z`, each one operation;
    - `ESCALATED_RUN`, `PARTITION_SCOPE_RUN`, `inFlightRun`, `queuedRun` and `QUEUE_TIMEOUT_RUN` become flat (`runOfAttempts` builds one run);
    - add `PENDING_RUN` (the next run of `inFlightRun`'s plan, `pending`, no attempt) and `OLDER_RUN_ID`, answered only by the by-id handler;
    - `RECONCILIATIONS`' started operations carry `run_id`.
  - `TablePage.stories.tsx`:
    - the `Maintenance*` stories open their run through the route (`${ORDERS}/maintenance?run=<id>`) and assert on the dialog;
    - add `MaintenanceRunPanel`: its play tabs to the first row's Open button, presses Enter, expects the heading focused, presses Escape and expects focus back on that button;
    - add `MaintenanceRunPanelPhone` (`PHONE`): the dialog is as wide as the window, and `expectNoHorizontalPageScroll` passes;
    - add `MaintenanceOlderRunLink`: `?run=OLDER_RUN_ID` opens it;
    - add `MaintenancePlanInFlight`: the in-flight run Running, its next run Pending;
    - `ReconciliationDrawer` checks the per-operation links.
- [ ] **Step 2: Run and watch them fail:** `<vitest> useOpenRecord MaintenanceTab anyRunInFlight compactionScopeText ReconciliationsTab`. `npx --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend tsc --noEmit -p /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend` lists every file the new client breaks.
- [ ] **Step 3: Implement** with design-system parts only (`src/data-platform/frontend/CLAUDE.md`). `MaintenanceRunPanel` takes the place of `RunDetail` and `OperationDetail`, and the attempts `DataTable` with its caption is deleted.
- [ ] **Step 4: Run and watch them pass:** `<vitest>`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit Tasks 3 to 8 together.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`. Expected: exit 0, with `contract-test` clean because `openapi.json` and the client were regenerated in Task 7. Commit `feat(table-maintenance): run one operation per maintenance run and open it in a side panel (KCL-95)`, with the backend, `openapi.json`, the generated client and the console.

### Task 9: Reconciliations open in the url, and one record reads by id

API change and console in one commit (contract-test and tsc).

**Files:**
- Create:
  - `TM/application/port/inbound/table_reconciliation/get_table_reconciliation/{__init__,input,output,use_case}.py`;
  - `TM/application/service/table_reconciliation/get_table_reconciliation.py`;
  - `TM/application/service/table_reconciliation/table_reconciliation_output_fields.py`. It moves `_item`, `_policy_target`, `_operation` and `_measurement` out of `list_table_reconciliations.py`, so that list and get build the same fields (`table_maintenance_run_output_fields.py` is the pattern);
  - `FE/components/tabs/ReconciliationPanel.tsx`.
- Modify:
  - `list_table_reconciliations.py`;
  - `bootstrap/container/{use_cases,build_use_cases}.py` and `TM/adapter/inbound/web/shared/web_use_cases.py`;
  - `TM/adapter/inbound/web/table_reconciliation/router.py`;
  - `openapi.json` and the generated client;
  - `FE/components/tabs/ReconciliationsTab.tsx` and its test;
  - `FE/stories/lakehouseHandlers.ts` and `FE/pages/TablePage.stories.tsx`.
- Test:
  - `tests/.../service/table_reconciliation/test_get_table_reconciliation_service.py` (new);
  - the reconciliation route test;
  - `ReconciliationsTab.test.tsx` and the stories.

**Interfaces:**
- Produces:
  - `GetTableReconciliationUseCaseInput(reconciliation_id: str)`. `GetTableReconciliationUseCaseOutput` has the fields of `ListTableReconciliationsUseCaseOutput.TableReconciliation`, built by `table_reconciliation_output_fields`. The nested `Measurement`, `Operation` and `PolicyTarget` classes are its own, one level deep.
  - A malformed id is `ValidationError` (422), and an unknown one `NotFoundError` (404).
  - `GET /v1/table-reconciliations/{reconciliation_id}` returns a `TableReconciliationApiResponse`. Its generated hook is `useGetTableReconciliation`.
  - The console:
    - `useOpenRecord("reconciliation")` replaces the local `shown` and `isOpen`;
    - the `Drawer` is `modal={false} contentKey={openId}`;
    - `ReconciliationPanel` is the `ReconciliationDetail` at HEAD, moved, with its record taken from the loaded pages or read by id, and the two messages of Global Constraints;
    - the title stays `headline(record)`.
  - The timeline line's `onSelect` opens the record, as at HEAD, and focus returns to it on close.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_reconciliation_by_id(): ...                  # recorded rc-1 → output equals the list's item for it
def test_get_unknown_reconciliation_is_not_found(): ...   # NotFoundError
def test_the_route_reads_one_reconciliation(client): ...  # GET /v1/table-reconciliations/{id} → body == list body[0]
def test_the_route_is_404_for_an_unknown_id(client): ...
```

  - `ReconciliationsTab.test.tsx`:
    - pressing a line sets `?reconciliation=<id>`;
    - `?reconciliation=<id>` of a record outside the first page reads it by id;
    - 404 shows "This reconciliation is no longer available";
    - a record of another table shows "This reconciliation belongs to another table";
    - Escape returns focus to the line.
  - Stories: `ReconciliationDrawer` opens through the route; add `ReconciliationPanelKeyboard` (Enter on a line, the heading focused, the next line opened with a click, Escape back to it) and `ReconciliationPanelPhone`.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "get_table_reconciliation or reconciliation_route" -v` and `<vitest> ReconciliationsTab`.
- [ ] **Step 3: Implement**, then `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`, `<vitest>` and the story tests.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): read one reconciliation by id and keep the open one in the url (KCL-95)`.

### Task 10: The Commits tab opens a commit in the side panel

Console only.

**Files:**
- Create: `FE/components/tabs/CommitPanel.tsx`.
- Modify: `FE/components/tabs/CommitsTab.tsx`, `CommitsTab.test.tsx` and `useCommitFilters.ts`, so a filter change keeps `snapshot`; `FE/pages/TablePage.stories.tsx`.
- Test: `CommitsTab.test.tsx` and the stories.

**Interfaces:**
- Produces:
  - `CommitRow`'s details button (`aria-label="Details of commit <id>"`) gains `aria-haspopup="dialog"`. Its `aria-expanded` is true while that commit's panel is open, and pressing it calls `open(commit.snapshot_id)`.
  - The inline `CommitDetail` is deleted.
  - `CommitPanel({ commit, schemaHref })` is a `DescriptionList`:
    - Snapshot id (mono, with `CopySnapshotId`), Parent (mono or "—");
    - Committed (timestamp), Writer (`writerLabel`);
    - Schema (`vN` linking to `?schema=N`, or "—");
    - Changes (`changeSummary` lines).
  - The panel then shows a heading "Summary" and a second `DescriptionList` of every `summary` entry, keys and values in mono, in the API's order.
  - The title is `commitTitle(commit)`, and the record comes from the loaded history. A snapshot not in it shows "This commit is not in the history shown. It may be outside the filters, or expired."

- [ ] **Step 1: Write the failing tests and stories.**
  - `CommitsTab.test.tsx`:
    - pressing "Details of commit <id>" opens `dialog` named by its title and sets `?snapshot=<id>`;
    - the panel shows `total-data-files` with its value;
    - changing the writer filter keeps `snapshot`, and closing keeps the filters;
    - `?snapshot=999` shows the missing message;
    - Escape returns focus to that commit's details button.
  - Stories: `CommitsPanel` (keyboard: Tab to the button, Enter, the heading focused, Escape back) and `CommitsPanelPhone` (`PHONE`, no horizontal scroll). `CommitsPhone` keeps passing.
- [ ] **Step 2: Run and watch them fail:** `<vitest> CommitsTab`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** `<vitest>` and the story tests.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`; commit `feat(console): open a commit in a side panel kept in the url (KCL-95)`.

### Task 11: e2e script and documentation

**Files:**
- Modify:
  - `platform/25-lakehouse-control-plane/e2e.sh` and `README.md`;
  - `src/data-platform/backend/CLAUDE.md`, `src/data-platform/frontend/CLAUDE.md` and `src/design-system/CLAUDE.md`;
  - `docs/agents/known-follow-ups.md` and `docs/agents/project-history.md`.

- [ ] **Step 1: e2e.** Read `e2e.sh` at HEAD first. Every run read becomes a flat run:
  - The `wait_for_new_run` selectors: `.trigger == "scheduled" and .operation == "rewrite_data_files"`.
  - `assert_runs_succeeded` checks `.status`, `.attempts`, `.metrics` and `.operation` on each run; `.operations[]` is gone.
  - `report_runs` prints one line per run: `run <id> <trigger> <operation> <status> attempts=<n> <metrics>`.
  - `assert_attempts_timed` reads `[.[] | .attempts[] | select(.status == "succeeded")]`.
  - `compaction_filters` reads `GET /v1/table-maintenance-runs/$1 | select(.operation == "rewrite_data_files") | .filters`.
  - The `ADDED` and `DELETED` sums select runs by `.operation`.
  - The manual run of four operations:
    - `ORDERS_RUNS` must hold four manual runs, one per operation (`[.[] | select(.trigger == "manual") | .operation] | sort == ["expire_snapshots", "remove_orphan_files", "rewrite_data_files", "rewrite_manifests"]`), with one `execution_ref` and one `created_at`.
    - The new `assert_runs_in_plan_order "${ORDERS}" "${ORDERS_RUNS}"` sorts the manual runs by the fixed order. Each run's `started_at` must be at or after the previous run's `finished_at`.
    - `ORDERS_MANUAL_RUN_ID` becomes the manual `rewrite_data_files` run.
    - `assert_manual_run_recorded uuid run_ids_json` requires a reconciliation whose started operations' `run_id`s are exactly the four manual run ids, each on its own operation: `[.operations[] | select(.result == "started") | {operation, run_id}]`.
  - The regions scheduled run is one run, `rewrite_data_files`, as before.
  - `assert_workflows_found_by_table` and `assert_prefixed_ids` take the compaction run's id, unchanged.
  - Run `uv run --directory /Users/kcl/Projects/retail-lakehouse pre-commit run shellcheck --all-files`.
- [ ] **Step 2: Docs.**
  - README:
    - The API table: "run history, one run per operation, with its parameters (`filters`, `procedure_args`), procedure numbers (`metrics`) and attempts".
    - Add the callback `POST /table-maintenance-runs/{run_id}/result`.
    - Add `GET /table-reconciliations/{id}`.
    - The Temporal table's `TableMaintenanceWorkflow` row: "one per table; runs the plan's runs, one per operation, in order; each run keeps its `mr-` id and the execution as `execution_ref`".
    - The manual-run paragraph: "raises the priority of the runs in flight, the one running and the ones still pending".
    - The KCL-94 sentence about `filters` "on each operation" becomes "on each compaction run".
    - e2e step 7: the four manual runs, one per operation, in order, and each linked from its reconciliation operation.
  - Backend `CLAUDE.md`: a short paragraph on:
    - the run aggregate (one operation, one `RunStatus`, the stored parameters, attempts with their `job_name`);
    - the child creating every run first and skipping the unreached;
    - the parent minting one id per operation;
    - `OperationOutcome.run_id`;
    - the submit reading its parameters from the run.
  - Frontend `CLAUDE.md`: replace line 44 (the Scope line and the attempts caption) with a rule. "**A record opens in a side panel** (Maintenance, Reconciliations, Commits): `Drawer modal={false}` beside the list, full page below 768px. The url names it (`?run=`, `?reconciliation=`, `?snapshot=`, `replace` navigation, through `useOpenRecord`). The panel holds a `DescriptionList` or a `Timeline`, never a table, and reads a record not in the list by id. The run panel shows the Scope of a compaction and an attempts timeline."
  - Design system `CLAUDE.md`: `DescriptionList` in the plain names; one line on `Drawer`'s `modal={false}` and `contentKey`, and `DataTable`'s `onOpenRow`.
  - `known-follow-ups.md`:
    - Remove the entry "The Maintenance tab loads only the latest 50 runs …". The panel now reads a run by id; the list itself still shows 50.
    - Reword the backoff entry: "a run reads `failed` during the backoff between its attempts".
    - Add, each tagged with the date it lands and KCL-95:
      - a child workflow terminated outright (not cancelled) never reaches `_finish`, so its later runs stay `pending`;
      - a reconciliation line with several runs shows no trailing run link; the panel lists them;
      - the four hand-rolled fact lists in the console could move to `DescriptionList`;
      - Back does not close a panel, because it uses `replace` navigation;
      - `procedure_args` is untyped JSON;
      - the Commits panel reads only the loaded history; the commits API has no read by id.
  - `project-history.md`: one KCL-95 line, dated the day it lands. It names:
    - one operation per run and the merged `RunStatus` (no `partially_failed`);
    - runs created first and run in order, with the unreached skipped;
    - the callback path;
    - `procedure_args` and `skip_reason`;
    - the per-operation `run_id` on reconciliations and `GET /v1/table-reconciliations/{id}`;
    - the three panels and their url parameters;
    - `DescriptionList` and the side-panel `Drawer`.

    It ends with "No migration: rebuild the cluster."
- [ ] **Step 3: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `docs(table-maintenance): describe one operation per run and check it in the e2e (KCL-95)`.

### Task 12: KCL-95 checks for the batched cluster verification (controller)

The controller runs these in the one rebuild batched with KCL-94, KCL-71 and KCL-98; this task does no rebuild of its own. The batch's rebuild (`task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `onboard KUBE_CONTEXT=retail-lakehouse`, then `apps:validate KUBE_CONTEXT=retail-lakehouse` exiting 0) comes first. Every API call below goes through the e2e script's `api` helper or the console.

- [ ] **Check 1: A manual run of four operations.**
  - `POST /v1/tables/{uuid}/maintenance` with all four operations on a managed table makes four runs, created at once and all `pending` (read the list right after the post).
  - The runs run in the fixed order: each run's `started_at` is at or after the previous run's `finished_at`, and only one SparkApplication of the table exists at any time (`kubectl get sparkapplications --context retail-lakehouse -n lakehouse-maintenance-operations -w`).
  - Each run's jobs are gone before the next run's job appears.
  - Its reconciliation record links each operation to its own run.
- [ ] **Check 2: A scheduled plan with two operations due.** A policy with `rewrite_data_files` and `expire_snapshots` blocks, both off target, gives one reconciliation, two runs and two links, compaction first.
- [ ] **Check 3: Raise.** While run 1 of Check 1 is queued, a manual run at `P0` raises the four runs: `GET` each shows `P0`. Only run 1's attempt is requeued (its job name changes, its attempt number does not).
- [ ] **Check 4: Skip.** While run 1 of a three-run plan runs, `temporal workflow cancel --workflow-id table-maintenance:table-uuid=<uuid>` through the e2e's `temporal_cli`. Runs 2 and 3 read `skipped` with "the table's maintenance stopped before this run started", and none stays `pending`.
- [ ] **Check 5: Callback path.** The api pod's log shows `POST /v1/table-maintenance-runs/<id>/result` answered 2xx for each run, and none on the old path.
- [ ] **Check 6: Temporal.** The table's maintenance execution's summary and its `MaintenanceOperations` still list every operation of the plan, and `TableUuid = "<uuid>"` finds it.
- [ ] **Check 7: Console, at 1280px and at 390px.**
  - In each of Maintenance, Reconciliations and Commits:
    - a click opens the side panel and the list stays clickable;
    - the next row shows in the same panel;
    - Escape returns focus to the row;
    - the url carries `?run=`, `?reconciliation=` or `?snapshot=`, and a reload opens the same panel.
  - At 390px the panel covers the page with no horizontal scroll.
  - A reconciliation's "Open maintenance run" opens the Maintenance tab with that run's panel.
  - A pending run reads "No attempt yet".
  - The `?run=` of another table's run reads "This run belongs to another table".
- [ ] **Check 8: e2e.** `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` passes, with `assert_runs_in_plan_order` and the four-run `assert_manual_run_recorded`. Then run `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`.
- [ ] **Record** the results on KCL-95 in a dated comment, and push only when the user asks.
