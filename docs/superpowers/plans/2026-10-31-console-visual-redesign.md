# Console Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the data platform console (`src/console/`) into a minimalist monochrome UI with light and dark mode, built on Tailwind CSS + shadcn/ui, with no change in behaviour.

**Architecture:** Tailwind v4 (CSS-first, `@tailwindcss/vite`) and shadcn/ui primitives copied into `src/components/ui/`; all colours, radii and fonts are tokens in `src/styles/globals.css`. A small theme module applies the `dark` class on `<html>`. Feature components keep their files and props and are rebuilt on the primitives page by page; `styles.css` is deleted at the end.

**Tech Stack:** React 19.3 + TypeScript 6 + Vite 8 + TanStack Query + react-router (existing); Tailwind CSS v4, shadcn/ui (Radix), lucide-react, Recharts (shadcn Chart), TanStack Table, `@fontsource-variable/geist`, `@fontsource-variable/geist-mono`; Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`

## Global Constraints

- Every existing feature, request, notice, empty / error state and gating behaves exactly as before; existing tests keep their behavioural assertions (selectors may change when a Radix primitive replaces a hand-written element).
- Tokens (exact values, light / dark): background `#ffffff` / `#000000`; surface (`--card`, sidebar) `#fafafa` / `#0a0a0a`; border `#ebebeb` / `#262626`; foreground `#171717` / `#ededed`; muted-foreground `#666666` / `#a1a1a1`; primary `#000000` / `#ffffff`; warning `#a35200` / `#ffb224`; destructive `#d93036` / `#ff6166`; success `#297a3a` / `#62c073`.
- Colour meaning: neutral for everything incl. not due / cooldown / disabled; `warning` = due operation or truncated count; `destructive` = error or failed run; `success` = succeeded run only.
- Radius 6px buttons / inputs, 8px panels, full for badges. No shadows on panels; one subtle shadow on overlays only. No gradients, no entrance animations.
- Fonts: Geist for UI, Geist Mono for identifiers (operation procedure names, snapshot ids, file paths, `execution_ref`, property keys / values, schema types); bundled via fontsource, never Google Fonts. Page title 24px / 600; section title 14px / 500; body 14px; secondary 13px; `tabular-nums` on number columns. Sentence case, no all-caps labels.
- Feature code (`src/components/` except `ui/`, `src/pages/`) uses token classes only — no raw hex values, no `[#…]` arbitrary colours.
- Theme: default System; switch offers Light / Dark / System; stored in `localStorage` key `console-theme` inside try/catch (failure → System); `dark` class on `<html>` set by an inline script in `index.html` before first paint.
- Do not downgrade React, Vite or TypeScript; if a library's newest release does not support them, use the newest release that does and note it. Exact version pins (no `^` / `~`).
- No backend change, no new pages. UI copy English.
- Console CHECKS before every commit: `npm --prefix src/console run typecheck`, `… run lint`, `… test -- --run`, `… run build`. Shell: no `cd`. Commits conventional, lines ≤ 100 chars, end with a blank line then `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`; on `main`, never push.

## Review Focus

1. `localStorage` throws (private mode, blocked storage) → the console still renders, theme follows the system. Test in Task 1.
2. Long identifiers (a 60-character table name, long file paths, snapshot ids) at 360px width → wrap or truncate inside their panel, never horizontal page scroll. Test in Task 3 (class assertion) and checked in Task 6's screenshots.
3. Status colours in dark mode → the due / error colours still read on `#000`/`#0a0a0a` (AA contrast). Pinned by the token table; checked in Task 6's screenshots.
4. Disabled Run maintenance on a non-active table → still explains why (tooltip / title) after moving to the Button primitive. Test in Task 3.
5. The not-in-catalog notice and the 404 path keep showing in the new layout, with the header still visible. Test in Task 3.

---

### Task 1: Tailwind, tokens, fonts, theme and app shell

**Files:**
- Modify: `src/console/package.json`, `package-lock.json`, `vite.config.ts` (add `@tailwindcss/vite`, alias `@` → `src`), `tsconfig.json` (`paths` `@/*`), `index.html` (inline theme script), `src/main.tsx` (import `styles/globals.css` and fonts), `src/App.tsx` (wrap routes in `ThemeProvider` + `AppShell`), `src/test/setup.ts` (jsdom shims: `ResizeObserver`, `matchMedia`, `hasPointerCapture` / `releasePointerCapture`, `scrollIntoView`)
- Create: `src/console/components.json`, `src/styles/globals.css`, `src/lib/utils.ts` (`cn`), `src/theme/ThemeProvider.tsx`, `src/theme/useTheme.ts`, `src/theme/themeStorage.ts`, `src/components/ThemeSwitch.tsx`, `src/components/AppShell.tsx`, `src/components/ui/{button,dropdown-menu,sheet,separator,tooltip}.tsx` (via the shadcn CLI)
- Test: `src/theme/themeStorage.test.ts`, `src/components/ThemeSwitch.test.tsx`, `src/components/AppShell.test.tsx`

**Interfaces:**
- Produces: `type ThemeChoice = "light" | "dark" | "system"`; `readThemeChoice(): ThemeChoice` and `writeThemeChoice(choice: ThemeChoice): void` in `themeStorage.ts` (key `console-theme`, try/catch, invalid or failing read → `"system"`); `useTheme(): { choice: ThemeChoice; resolved: "light" | "dark"; setChoice(c: ThemeChoice): void }`; `<AppShell>{children}</AppShell>` with a sidebar (product name "Lakehouse" linking to `/`, nav item "Tables" linking to `/`, `ThemeSwitch` at the bottom) that becomes a top bar + `Sheet` menu below the `md` breakpoint. Token classes from shadcn's names plus `warning` and `success` (`bg-warning`, `text-warning`, `text-success`).
- `styles.css` stays imported for now so pages keep working until Tasks 2–5 move them.

- [ ] **Step 1: Write failing tests**: `themeStorage.test.ts` — `readThemeChoice` returns `"system"` when nothing is stored, when the value is `"blue"`, and when `localStorage.getItem` throws; `writeThemeChoice("dark")` stores `"dark"`, and does not throw when `setItem` throws. `ThemeSwitch.test.tsx` — choosing Dark adds `dark` to `document.documentElement.classList` and stores `"dark"`; choosing System with `matchMedia('(prefers-color-scheme: dark)')` mocked to match adds `dark`, mocked not to match removes it. `AppShell.test.tsx` — renders a navigation landmark with a "Tables" link to `/` and the children.
- [ ] **Step 2: Run** `npm --prefix src/console test -- --run` — Expected: FAIL (modules missing).
- [ ] **Step 3: Implement**: install Tailwind v4 + `@tailwindcss/vite`, run `npx shadcn@latest init` (style new-york, base neutral, CSS variables) with `--cwd src/console`, replace the generated colours with the Global Constraints tokens for `:root` and `.dark`, add `--warning` / `--success` and register them in `@theme inline`; set `--radius: 0.5rem` and font variables (`--font-sans: "Geist Variable"`, `--font-mono: "Geist Mono Variable"`). The `index.html` script reads `console-theme` in try/catch and sets `dark` when the choice is dark, or system and `prefers-color-scheme: dark` matches. `ThemeProvider` keeps the class in sync and listens to `matchMedia` changes while the choice is system.
- [ ] **Step 4: Run** console CHECKS — Expected: PASS, and every existing test still passes.
- [ ] **Step 5: Commit** `feat(console): add Tailwind, shadcn/ui tokens, theme switching and the app shell`

### Task 2: Table list as a Data Table

**Files:**
- Modify: `src/pages/TableListPage.tsx`, `src/pages/TableListPage.test.tsx`
- Create: `src/components/ui/{table,input,select,badge,skeleton,alert}.tsx` (shadcn CLI), `src/components/StatusBadge.tsx`, `src/components/PageHeader.tsx`

**Interfaces:**
- Consumes: Task 1 shell and tokens.
- Produces: `<StatusBadge status={string} />` (lowercase wire value in; renders the capitalised word, neutral outline for active / paused / excluded / dropped) and `<PageHeader title={string} breadcrumb?={string} actions?={ReactNode}>{meta}</PageHeader>` — both reused by Task 3.

- [ ] **Step 1: Failing tests** (keep all existing list tests' assertions): `sorts by name ascending by default`; `clicking the Updated header sorts by updated_at descending then ascending` (assert row order); loading shows skeleton rows (`aria-busy` on the table container).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** with TanStack Table (sorting state in component state; status filter as a shadcn Select and the search Input stay above the table). Name cell in Geist Mono; updated in `tabular-nums`.
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): show the table list as a sortable data table`

### Task 3: Table page header, tabs, Commits, Maintenance, Properties and the run dialog

**Files:**
- Modify: `src/pages/TablePage.tsx`, `src/components/TableHeader.tsx`, `src/components/RunMaintenanceDialog.tsx`, `src/components/tabs/{CommitsTab,MaintenanceTab,PropertiesTab}.tsx`, their tests and `TablePage.test.tsx`
- Create: `src/components/ui/{tabs,dialog,checkbox,label}.tsx` (shadcn CLI), `src/components/Panel.tsx`

**Interfaces:**
- Consumes: `StatusBadge`, `PageHeader` (Task 2).
- Produces: `<Panel title={string} actions?={ReactNode}>{children}</Panel>` — bordered 8px panel with a title row on surface, no shadow; reused by Tasks 4 and 5. `RunMaintenanceDialog` keeps its props (`initialOperations?: string[]` and the existing ones) but renders as a shadcn `Dialog` opened from the header button.
- Tabs keep their URL segments (`overview`, `commits`, `maintenance`, `properties`, `settings`) and are rendered with shadcn `Tabs` driven by the route.

- [ ] **Step 1: Failing tests**: `RunMaintenanceDialog` opens as `role="dialog"`, `Escape` closes it and no POST is sent; the disabled Run maintenance button on a paused table still exposes its explanation (accessible description or tooltip text "Only an active table can run maintenance", the current wording); the header title element has the `break-words` (or `truncate` + `title`) class so a 60-character name cannot overflow; the not-in-catalog notice still renders with the header (existing test kept).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**: header via `PageHeader` (breadcrumb `catalog / namespace` as plain text, meta line with `StatusBadge` and the metadata numbers), tabs via shadcn Tabs, Commits / Maintenance as shadcn Table inside `Panel` with expandable rows (chevron icon), Properties as a two-column key/value table in Geist Mono; failed runs use `text-destructive`, succeeded runs `text-success`.
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): restyle the table page, its tabs and the run dialog`

### Task 4: Overview panels and the Freshness chart

**Files:**
- Modify: `src/components/tabs/OverviewTab.tsx`, `src/components/{HealthPanel,StoragePanel,FreshnessPanel,SchemaPanel,RecentCommitsPanel,LastRunPanel}.tsx` and their tests
- Create: `src/components/ui/chart.tsx` (shadcn CLI, adds Recharts)

**Interfaces:**
- Consumes: `Panel` (Task 3); `hourlyCommitBuckets` / `writerMix` from `freshness.ts` (unchanged).
- Layout: Health and Storage side by side at `lg` and up, one column below; Freshness full width below; then schema / partition spec, recent commits, last run.

- [ ] **Step 1: Failing tests** (keep all existing Overview / Health / Storage assertions): Freshness renders a legend with one entry per operation present in the buckets (e.g. `append`, `overwrite`); a due Health line's text has the `text-warning` class and a cooldown line does not; the storage bar shows current and old-snapshot segments with accessible labels ("Current snapshot", "Only in old snapshots").
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**: Freshness as a shadcn `ChartContainer` stacked bar chart, one grey step per operation (darkest = append) defined as chart config tokens in both themes, tooltip listing counts per operation; operation procedure names in Geist Mono; numbers `tabular-nums`; storage split as a two-segment bar (foreground / muted).
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): restyle the overview panels and chart commit freshness`

### Task 5: Settings form and the reset confirmation

**Files:**
- Modify: `src/components/tabs/SettingsTab.tsx`, `src/components/{SettingsForm,SettingsFieldGroup}.tsx`, `SettingsTab.test.tsx`
- Create: `src/components/ui/{alert-dialog,switch}.tsx` (shadcn CLI)

**Interfaces:**
- Consumes: `Panel` (Task 3); Input / Select / Label / Checkbox primitives from Tasks 2–3.

- [ ] **Step 1: Failing tests** (keep the four existing SettingsTab assertions): Reset to preset opens `role="alertdialog"`, `Escape` closes it and no PUT is sent; each operation group renders inside a panel titled with its procedure name; the enabled toggle is a `switch` role.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** one `Panel` per operation, fields as Label + Input / Select / Switch, a sticky footer row with Save; the 422 detail as a destructive `Alert`.
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): restyle the settings form with a reset confirmation dialog`

### Task 6: Remove the old stylesheet, enforce tokens, document, deploy and check visually

**Files:**
- Delete: `src/console/src/styles.css` (and its import)
- Create: `src/console/src/test/noRawColors.test.ts`
- Modify: `CLAUDE.md` (console UI rules + Project Status line), `src/console/README.md`

- [ ] **Step 1: Failing test** `noRawColors.test.ts`: reads every `.tsx` under `src/components` (excluding `src/components/ui/`) and `src/pages`, and fails if any matches `/#[0-9a-fA-F]{3,8}\b/` or `/\[#/`; also fails while `src/styles.css` exists.
- [ ] **Step 2: Run** — Expected: FAIL (stylesheet still present, or stray colours).
- [ ] **Step 3: Implement**: delete `styles.css`, move anything still needed into Tailwind classes; add to CLAUDE.md a "Console UI" section with the spec's "Rules for future pages" and a Project Status history line for 2026-10-31.
- [ ] **Step 4: Run** console CHECKS and `docker build -t console:dev src/console` — Expected: PASS / image builds.
- [ ] **Step 5: Deploy** `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`, then `validate.sh` — Expected: "Lakehouse control plane is ready".
- [ ] **Step 6: Visual check**: port-forward `service/platform-gateway-istio` 18080:80 in `istio-ingress` and take screenshots (Playwright via `npx playwright screenshot` or the webapp-testing skill) of `/console/`, the `tm_e2e_orders` Overview, Commits and Settings tabs in light and dark, at 1280px and 375px wide; save them under `$CLAUDE_JOB_DIR/tmp/screens/`. Check: no horizontal page scroll at 375px, due / error colours readable in dark, no unstyled elements. Fix and recheck anything that fails.
- [ ] **Step 7: Commit** `refactor(console): drop the legacy stylesheet and enforce design tokens`
