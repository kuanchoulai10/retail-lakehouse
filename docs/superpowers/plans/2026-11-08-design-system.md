# Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `src/design-system` (Serendie tokens, three themes, Radix + Tailwind 4 components, Storybook with axe and keyboard tests) and move the console onto it completely.

**Architecture:** An npm workspace package consumed as TypeScript source by the console. Three token layers: Serendie `--sd-*` → design-system semantic tokens (`--ds-*`) → Tailwind utilities. Components wrap Radix primitives, follow Serendie's anatomy and names, and size themselves by Serendie's two window classes. The console migrates in four steps behind a temporary alias block so every commit stays green.

**Tech Stack:** React 19, Vite 8, TypeScript 6, Tailwind CSS 4, `radix-ui`, TanStack Table 9, Recharts 3, `@serendie/design-token`, `@serendie/symbols`, Fontsource Noto Sans, Storybook (react-vite) with `@storybook/addon-a11y` and `@storybook/addon-vitest`, Vitest 5 (jsdom for units, browser mode with Playwright Chromium for stories).

**Spec:** `docs/superpowers/specs/2026-11-08-design-system-design.md`

## Global Constraints

- Stack fixed: React 19, Vite 8, Tailwind CSS 4, Radix (`radix-ui`). No `@serendie/ui`, Ark UI or Panda CSS anywhere in the dependency tree.
- Every dependency pinned to an exact version (no `^` or `~`), as the console does today.
- Themes: KONJO (default, no attribute), ASAGI (`data-panda-theme="asagi"`), KURIKAWA (`data-panda-theme="kurikawa"`) on `<html>`. Light values only. No dark mode. No SUMIRE, TSUTSUJI or `konjo-dark`. No colour derived by us.
- Window classes split at 768px (`--sd-system-dimension-breakpoint-expanded`): below it Serendie `*_compact` typography and touch sizes (targets ≥ 44 × 44px); at or above it `*_expanded` typography and dense sizes. `@media (pointer: coarse)` keeps the 44px target minimum at any width.
- Expanded sizing: controls (buttons, inputs, selects, nav items) 36px high; table rows 36px. Compact: controls and rows 44px.
- Status: badges use `{positive|notice|negative}Container` with `on…Container` text. Bare status text or icons on a surface use `negative`, `chart-mark-positive-05`, `chart-mark-notice-05`. `positive` and `notice` are never text or icon colours on a surface.
- Contrast floor, every theme: 4.5:1 text, 3:1 large text and UI parts (borders of inputs, focus ring, icons).
- Fonts: Noto Sans (text), Noto Sans Mono (identifiers, code), self-hosted via Fontsource. Never bundle `SerendieOfficeVF`.
- Icons only from `@serendie/symbols`, reached through the design system. No `lucide-react` at the end.
- Console code (`src/data-platform/frontend/src/**` except tests) never references `--sd-*`, raw colours, `radix-ui`, `@serendie/*` or `lucide-react`, and imports the design system only from `@retail-lakehouse/design-system`.
- Serendie component names where Serendie has one: `Button`, `IconButton`, `Badge`, `Divider`, `TextField`, `TextArea`, `CheckBox`, `Switch`, `Select`, `ModalDialog`, `DropdownMenu`, `Tooltip`, `Drawer`, `TopAppBar`, `Breadcrumbs`, `Tabs`, `List`, `DataTable`, `Banner`. Components Serendie lacks get plain names (`AlertDialog`, `SideNavigation`, `TitleBar`, `AppLayout`, `Panel`, `EmptyState`, `Skeleton`, `StatusBadge`, `ThemePicker`, `ChartContainer`).
- Ported Serendie values or source keep the MIT notice in a header comment naming `serendie/serendie` and the file.
- Product UI shows no Serendie or Mitsubishi Electric names or logos; the design-system README carries the credit line: "Uses Serendie design tokens and symbols (MIT, Mitsubishi Electric)."
- Existing console tests keep their behavioural assertions; only selectors, setup and imports may change.
- Every commit keeps the console building and `task pre-pr` green. Conventional commits, lowercase subject, lines ≤ 100 chars, ending with the line `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. Stage files by explicit path; never stage `docs/architecture.excalidraw.svg` or anything under `temp/`. No `cd`; use `npm --prefix` and absolute paths.

## Review Focus

1. **Stored theme is missing, stale or unreadable** (old `"dark"`, a typo, storage blocked in private mode): the console renders KONJO and does not throw. Pinned in Task 3.
2. **Long identifiers at phone width** (a 60-character table name in the title bar or breadcrumbs): the text wraps or truncates and the page never scrolls sideways. Pinned in Tasks 7 and 11.
3. **A wide table on a phone**: the table scrolls inside its own container with the first column sticky; the page itself does not widen. Pinned in Task 8.
4. **Navigating from the phone Drawer**: choosing a link closes the Drawer and moves focus to the new page's main region; Escape closes it and returns focus to the menu button. Pinned in Task 7.
5. **Theme switched while an overlay is open** (a dialog or menu portalled outside the app root): the overlay recolours too, because the attribute sits on `<html>`. Pinned in Task 6.

---

## File Structure

```
package.json                                   root: private, workspaces, commitlint devDeps
package-lock.json                              single lockfile (replaces the console's)
src/design-system/
  package.json                                 @retail-lakehouse/design-system, exports "." and "./styles.css"
  tsconfig.json  vite.config.ts  eslint.config.js  README.md  CLAUDE.md
  .storybook/main.ts  .storybook/preview.tsx  .storybook/vitest.setup.ts
  src/index.ts                                 the only public entry
  src/lib/cn.ts                                class merging
  src/styles/index.css                         entry: tailwind, fonts, serendie tokens, semantic tokens, utilities
  src/styles/semantic.css                      --ds-* semantic tokens per theme
  src/styles/typography.css                    type-* utilities, window-class switch
  src/styles/density.css                       h-control, min-h-row utilities, window-class + pointer switch
  src/tokens/semanticTokens.ts                 SEMANTIC_TOKENS list, CONTRAST_PAIRS
  src/tokens/resolveThemeTokens.ts             parses CSS → resolved hex per theme (used by tests)
  src/tokens/contrastRatio.ts                  WCAG contrast
  src/theme/themes.ts                          ThemeName, THEMES, DEFAULT_THEME, THEME_STORAGE_KEY
  src/theme/themeStorage.ts  applyTheme.ts  ThemeProvider.tsx  themeContext.ts  useTheme.ts
  src/icons/index.ts                           re-exported Serendie symbols the console uses
  src/components/<Name>/<Name>.tsx, <Name>.stories.tsx, <Name>.test.tsx (unit, when needed)
  src/stories/Foundations.stories.tsx          colour, type, density swatches
src/data-platform/frontend/                    console; depends on the design system
  Dockerfile  Dockerfile.dockerignore          image built from the repo root
platform/25-lakehouse-control-plane/build.sh   console tag covers the design system
tasks/checks.yml  tasks/dev.yml                new test tasks, root npm install
docs/adr/0008-design-system-on-serendie-tokens.md
```

---

### Task 1: Workspace, package skeleton and console image

**Files:**
- Modify: `package.json` (root), `tasks/dev.yml`, `tasks/checks.yml`, `platform/25-lakehouse-control-plane/build.sh`, `src/data-platform/frontend/package.json`, `src/data-platform/frontend/Dockerfile`
- Create: `src/design-system/{package.json,tsconfig.json,vite.config.ts,eslint.config.js,README.md}`, `src/design-system/src/index.ts`, `src/design-system/src/lib/cn.ts`, `src/design-system/src/lib/cn.test.ts`, `src/data-platform/frontend/Dockerfile.dockerignore`
- Delete: `src/data-platform/frontend/package-lock.json`

**Interfaces:**
- Produces: package `@retail-lakehouse/design-system` with `exports: { ".": "./src/index.ts", "./styles.css": "./src/styles/index.css" }`; `cn(...inputs: ClassValue[]): string` (clsx + tailwind-merge) exported from the package root; console dependency `"@retail-lakehouse/design-system": "0.0.0"`; Taskfile tasks `checks:unit-test-design-system` and `checks:lint-design-system`.

- [ ] **Step 1: Write the failing test** `src/design-system/src/lib/cn.test.ts`

```ts
import { cn } from "./cn";

it("merges conflicting tailwind classes, last wins", () => {
  expect(cn("px-2 text-sm", undefined, false, "px-4")).toBe("text-sm px-4");
});
```

- [ ] **Step 2: Create the workspace and package, run the test, watch it fail**
  - Root `package.json`: `"name": "retail-lakehouse"`, `"private": true`, `"workspaces": ["src/design-system", "src/data-platform/frontend"]`; keep the commitlint devDeps (pin exact) and the AGPL licence.
  - Design-system `package.json`: `"private": true`, `"version": "0.0.0"`, `"type": "module"`, scripts `test` (`vitest`), `lint` (`eslint .`), `typecheck` (`tsc --noEmit`); the `exports` above; `peerDependencies` react/react-dom 19.3.1; dependencies `clsx`, `tailwind-merge`, `class-variance-authority` 0.7.1, `radix-ui` 1.8.1 (exact versions).
  - `tsconfig.json`, `eslint.config.js`, `vite.config.ts` (vitest `environment: "jsdom"`) mirror the console's.
  - Remove the console's `package-lock.json`; run `npm install` at the repo root to produce the single root lockfile.
  - Run: `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system test -- --run` → FAIL, `cn` not found.

- [ ] **Step 3: Implement `cn` in `src/lib/cn.ts`** and export it from `src/index.ts`. README holds the credit line from Global Constraints and one paragraph on purpose.

- [ ] **Step 4: Wire tasks and the image**
  - `tasks/dev.yml`: `install-commitlint` becomes `install-node-deps` running `npm clean-install` at the repo root.
  - `tasks/checks.yml`: add `unit-test-design-system` (`npm --prefix src/design-system test -- --run`) to `unit-test` deps; add `lint-design-system` (`lint` + `typecheck`) and call it from `pre-pr` right after `lint-frontend`.
  - Console `Dockerfile` builds from the repo root: copy `package.json`, `package-lock.json`, both workspace `package.json` files, `npm ci --workspace src/data-platform/frontend --include-workspace-root=false`, copy both workspace folders, `npm --prefix src/data-platform/frontend run build`, nginx stage copies `src/data-platform/frontend/dist`.
  - `Dockerfile.dockerignore` (BuildKit per-Dockerfile ignore, allowlist): ignore `*`, allow `package.json`, `package-lock.json`, `src/design-system/**`, `src/data-platform/frontend/**`, re-ignore `**/node_modules`, `**/dist`, `**/storybook-static`.
  - `build.sh`: `source_tag` accepts several paths and hashes them together; the console tag is `source_tag "${CONSOLE_DIR}" "${DESIGN_SYSTEM_DIR}" "${REPO_ROOT}/package.json" "${REPO_ROOT}/package-lock.json"`; `build_and_load console` passes `--file "${CONSOLE_DIR}/Dockerfile"` with context `${REPO_ROOT}`.

- [ ] **Step 5: Verify**
  - `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system test -- --run` → PASS.
  - `task --dir /Users/kcl/Projects/retail-lakehouse pre-pr` → green.
  - `docker build --file /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend/Dockerfile /Users/kcl/Projects/retail-lakehouse` → succeeds; `bash -n` on `build.sh` passes.

- [ ] **Step 6: Commit** `build(design-system): add the design-system workspace and build the console from the root`

---

### Task 2: Serendie tokens, semantic layer, typography and density

**Files:**
- Create: `src/design-system/src/styles/{index.css,semantic.css,typography.css,density.css}`, `src/design-system/src/tokens/{semanticTokens.ts,resolveThemeTokens.ts,contrastRatio.ts}`, tests `src/design-system/src/tokens/{contrastRatio.test.ts,themeTokens.test.ts}`
- Modify: `src/design-system/package.json` (deps `@serendie/design-token` 1.4.6, `tailwindcss` 4.3.3, `@fontsource-variable/noto-sans`, `@fontsource-variable/noto-sans-mono`, exact)

**Interfaces:**
- Produces:
  - CSS entry `@retail-lakehouse/design-system/styles.css`: imports `tailwindcss`, both Fontsource packages, `@serendie/design-token/tokens.css`, then `semantic.css`, `typography.css`, `density.css`; `@source "../"` so the package's own classes are generated; `@theme inline` maps each semantic token to a Tailwind colour (`--color-surface: var(--ds-surface)` …), `--font-sans: "Noto Sans Variable", ui-sans-serif, system-ui, sans-serif`, `--font-mono: "Noto Sans Mono Variable", ui-monospace, monospace`, radii `--radius-sm/md/lg/xl` from `--sd-system-dimension-radius-small/medium/large/extraLarge`.
  - Semantic tokens (`--ds-<name>`, Tailwind `bg-<name>`, `text-<name>`, `border-<name>`): `surface`, `surface-container`, `surface-container-dim`, `on-surface`, `on-surface-variant`, `outline`, `outline-dim`, `primary`, `on-primary`, `primary-container`, `on-primary-container`, `hovered`, `disabled`, `on-disabled`, `scrim`, `focus-ring`, `positive-container`, `on-positive-container`, `positive-text`, `notice-container`, `on-notice-container`, `notice-text`, `negative`, `negative-container`, `on-negative-container`, `negative-text`, `chart-1` … `chart-5`. Mapping: `positive-text → --sd-system-color-chart-mark-positive-05`, `notice-text → --sd-system-color-chart-mark-notice-05`, `negative-text → --sd-system-color-impression-negative`, `focus-ring → --sd-system-color-impression-primary`; the rest to the same-named Serendie `component-*`, `impression-*`, `interaction-*` role. Charts: `chart-1` primary, `chart-2` positive-05, `chart-3` notice-04, `chart-4` negative, `chart-5` outline-dim (pick Serendie `chart-mark-*` tokens; all must be Serendie values).
  - `semantic.css` declares the mapping once on `:root`; because it only references `--sd-*`, the three themes follow automatically from Serendie's `[data-panda-theme=…]` blocks.
  - Utilities `type-display-small`, `type-headline-small`, `type-title-large`, `type-title-medium`, `type-title-small`, `type-body-large`, `type-body-medium`, `type-body-small`, `type-label-large`, `type-label-medium`, `type-label-small`, each `font: var(--sd-system-typography-<role>_compact) var(--font-sans)` and the `_expanded` value at `@media (width >= 768px)`; `type-code` uses `body-small` with `--font-mono`.
  - Utilities `h-control` / `min-h-control` (44px; 36px at ≥ 768px unless `pointer: coarse`), `min-h-row` (44px; 36px likewise), `size-touch` (44px always).
  - `SEMANTIC_TOKENS: readonly SemanticToken[]`, `CONTRAST_PAIRS: readonly { foreground: SemanticToken; background: SemanticToken; minimum: 4.5 | 3 }[]`, `resolveThemeTokens(theme: ThemeName): Record<SemanticToken, string>` (hex, uppercase), `contrastRatio(foreground: string, background: string): number` (WCAG 2.x relative luminance, alpha ignored after compositing on white).
  - `ThemeName = "konjo" | "asagi" | "kurikawa"` lives in `src/theme/themes.ts` (create the file here with only the type and `THEMES`; Task 3 adds the rest).

- [ ] **Step 1: Write the failing tests**

```ts
// contrastRatio.test.ts
it("matches WCAG reference values", () => {
  expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
  expect(contrastRatio("#2EAB80", "#FFFFFF")).toBeCloseTo(2.9, 1);
  expect(contrastRatio("#816E00", "#FFFFFF")).toBeCloseTo(5.04, 1);
});

// themeTokens.test.ts
describe.each(THEMES.map((t) => t.name))("%s", (theme) => {
  const tokens = resolveThemeTokens(theme);
  it("defines every semantic token as a colour", () => {
    for (const name of SEMANTIC_TOKENS) expect(tokens[name]).toMatch(/^#[0-9A-F]{6}([0-9A-F]{2})?$/);
  });
  it.each(CONTRAST_PAIRS)("$foreground on $background meets $minimum:1", ({ foreground, background, minimum }) => {
    expect(contrastRatio(tokens[foreground], tokens[background])).toBeGreaterThanOrEqual(minimum);
  });
});
it("themes really differ", () => {
  expect(resolveThemeTokens("asagi").primary).not.toBe(resolveThemeTokens("konjo").primary);
  expect(resolveThemeTokens("kurikawa").primary).toBe("#8F3D15");
});
```

`CONTRAST_PAIRS` (4.5 unless noted): `on-surface`/`surface`, `on-surface`/`surface-container`, `on-surface-variant`/`surface`, `on-surface-variant`/`surface-container`, `on-primary`/`primary`, `on-primary-container`/`primary-container`, `primary`/`surface` (text links), `on-positive-container`/`positive-container`, `on-notice-container`/`notice-container`, `on-negative-container`/`negative-container`, `positive-text`/`surface`, `notice-text`/`surface`, `negative-text`/`surface`, `focus-ring`/`surface` (3), `outline-dim`/`surface` (3).

- [ ] **Step 2: Run, watch them fail** — `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system test -- --run src/tokens` → FAIL (modules missing).

- [ ] **Step 3: Implement** the CSS files and the three TS modules. `resolveThemeTokens` reads `semantic.css` and `@serendie/design-token/tokens.css` as raw text (`?raw`), takes the `:where(:root,:host)` block as KONJO, overlays the `[data-panda-theme=<name>]` block for the others, and resolves `var(--x)` chains.

- [ ] **Step 4: Verify** — same command → PASS. If a pair fails in a theme, map that semantic token to a different Serendie value that passes and record why in a comment in `semantic.css`; never derive a colour.

- [ ] **Step 5: Commit** `feat(design-system): map serendie tokens to semantic tokens for three themes`

---

### Task 3: Theme runtime

**Files:**
- Modify: `src/design-system/src/theme/themes.ts`
- Create: `src/design-system/src/theme/{themeStorage.ts,applyTheme.ts,themeContext.ts,ThemeProvider.tsx,useTheme.ts}`, tests `themeStorage.test.ts`, `ThemeProvider.test.tsx`
- Modify: `src/design-system/src/index.ts`

**Interfaces:**
- Produces: `THEMES: readonly { name: ThemeName; label: string }[]` = `[{konjo,"Konjo"},{asagi,"Asagi"},{kurikawa,"Kurikawa"}]`; `DEFAULT_THEME = "konjo"`; `THEME_STORAGE_KEY = "ds-theme"`; `THEME_ATTRIBUTE = "data-panda-theme"`; `readTheme(): ThemeName`; `writeTheme(theme: ThemeName): void`; `applyTheme(root: HTMLElement, theme: ThemeName): void` (removes the attribute for KONJO, sets it otherwise); `<ThemeProvider>`; `useTheme(): { theme: ThemeName; setTheme(theme: ThemeName): void }` (throws outside the provider). All exported from the package root.

- [ ] **Step 1: Write the failing tests**

```ts
it.each([null, "dark", "system", "sumire", "KONJO"])("reads %s as konjo", (stored) => {
  stored === null ? localStorage.removeItem(THEME_STORAGE_KEY) : localStorage.setItem(THEME_STORAGE_KEY, stored);
  expect(readTheme()).toBe("konjo");
});
it("falls back to konjo when storage throws", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(readTheme()).toBe("konjo");
});
it("survives a write that throws", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(() => writeTheme("asagi")).not.toThrow();
});
it("applies asagi as an attribute and konjo as none", () => {
  applyTheme(document.documentElement, "asagi");
  expect(document.documentElement.getAttribute("data-panda-theme")).toBe("asagi");
  applyTheme(document.documentElement, "konjo");
  expect(document.documentElement.hasAttribute("data-panda-theme")).toBe(false);
});
it("ThemeProvider applies and persists the chosen theme", async () => {
  // render a consumer that calls setTheme("kurikawa"); expect the attribute and localStorage "ds-theme" = "kurikawa"
});
```

- [ ] **Step 2: Run, watch them fail** — `npm --prefix … test -- --run src/theme` → FAIL.
- [ ] **Step 3: Implement** the modules (storage mirrors the console's current try/catch pattern).
- [ ] **Step 4: Verify** → PASS.
- [ ] **Step 5: Commit** `feat(design-system): add the three-theme runtime`

---

### Task 4: Storybook, story tests, axe and the foundations story

**Files:**
- Create: `src/design-system/.storybook/{main.ts,preview.tsx,vitest.setup.ts}`, `src/design-system/src/stories/Foundations.stories.tsx`
- Modify: `src/design-system/package.json` (Storybook react-vite, `@storybook/addon-a11y`, `@storybook/addon-vitest`, `@vitest/browser`, `playwright` — current stable, exact), `src/design-system/vite.config.ts` (two Vitest projects: `unit` jsdom over `src/**/*.test.{ts,tsx}`, `storybook` browser mode Chromium via the addon), `tasks/checks.yml`, `tasks/dev.yml`, `.gitignore` (`storybook-static`)

**Interfaces:**
- Produces:
  - `preview.tsx`: imports `../src/styles/index.css`; a `theme` global toolbar (Konjo/Asagi/Kurikawa) whose decorator calls `applyTheme(document.documentElement, …)`; viewports `phone` (390 × 844) and `desktop` (1280 × 800); `parameters.a11y.test = "error"` so axe violations fail story tests.
  - Package scripts `storybook` (dev on port 6006), `build-storybook`, `test` runs project `unit`, `test:stories` runs project `storybook`.
  - Taskfile: `checks:component-test` (`npm --prefix src/design-system run test:stories`) called from `pre-pr` after `unit-test`; `dev.yml` gains `install-playwright` (`npx --prefix src/design-system playwright install chromium`) in `sync`.
  - Story helper `expectNoHorizontalPageScroll(canvasElement: HTMLElement): void` in `src/stories/assertions.ts` — asserts `document.documentElement.scrollWidth <= document.documentElement.clientWidth`.
- `Foundations.stories.tsx`: stories `Colours` (every semantic token as a labelled swatch), `Typography` (every `type-*` role), `Density` (`h-control`, `min-h-row` samples). A play test on `Colours` checks every `SEMANTIC_TOKENS` entry renders a swatch.

- [ ] **Step 1: Write the failing story test** — the `Colours` story's `play` asserts one swatch per `SEMANTIC_TOKENS` entry; run `npm --prefix … run test:stories` → FAIL (no Storybook config yet).
- [ ] **Step 2: Add the config, preview and stories.**
- [ ] **Step 3: Verify** — `test:stories` → PASS with axe on; `build-storybook` succeeds; `task --dir /Users/kcl/Projects/retail-lakehouse pre-pr` green.
- [ ] **Step 4: Commit** `feat(design-system): add storybook with theme toolbar, axe and story tests`

---

### Tasks 5–8: Components

Rules for every component task:
- One folder per component: `src/components/<Name>/<Name>.tsx`, `<Name>.stories.tsx`, plus `<Name>.test.tsx` only for logic stories cannot show. Export from `src/index.ts`.
- Behaviour from the matching `radix-ui` primitive; never re-implement focus, dismissal or ARIA that Radix provides. Forward refs and spread remaining props so `asChild` composition works.
- Variants with `cva`. Colours only through semantic utilities; sizes through `h-control`, `min-h-row`, `size-touch`, `type-*`.
- Visible focus ring on every focusable element: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring`.
- Stories: every variant and state (default, hover via `pseudo` where useful, focused, disabled, invalid, loading where relevant) on both viewports. Each story's docs description records where its expanded sizes depart from Serendie.
- Keyboard play tests (Testing Library `userEvent` inside `play`) for every interactive component, asserting at minimum: Tab reaches it, focus ring visible (`toHaveFocus` plus computed outline width ≠ `0px`), activation keys work, Escape dismisses overlays and focus returns to the trigger, arrow keys move within menus, selects, tabs and radio-like groups.
- Design spec: the Serendie docs page for the component and the `@serendie/ui` recipe in `serendie/serendie` `packages/ui/src/components/<Name>` (read on GitHub; do not install `@serendie/ui`).

### Task 5: Actions and display primitives

**Files:** `src/design-system/src/components/{Button,IconButton,Badge,StatusBadge,Divider,Skeleton,Tooltip}/…`, `src/design-system/src/icons/index.ts`, `src/design-system/package.json` (`@serendie/symbols` 1.0.3)

**Interfaces:**
- `Button`: props `styleType?: "filled" | "outlined" | "ghost"` (default `"filled"`), `size?: "medium" | "small"`, `isLoading?: boolean`, `asChild?: boolean`, plus `button` props. Small is 32px in expanded and still meets 44px under `pointer: coarse`.
- `IconButton`: `icon: ReactNode`, `"aria-label": string` (required in the type), `styleType`, `shape?: "circle" | "rectangle"`.
- `Badge`: neutral count/label chip. `StatusBadge`: `status: "positive" | "notice" | "negative" | "neutral"`, children text; uses container/on-container tokens.
- `Divider`, `Skeleton` (`aria-hidden`), `Tooltip` (+ `TooltipProvider`).
- `icons/index.ts`: re-export the Serendie symbols that replace each lucide icon the console uses today: ArrowDown, ArrowUp, BookOpen, Check, ChevronDown, ChevronRight, ChevronUp, ChevronsUpDown, Menu, MoreHorizontal, ScanSearch, SlidersHorizontal, Table2, Trash2, X (Monitor, Moon, Sun go away with dark mode). Choose by meaning, export under the Serendie name, and list the mapping in the task report. Export `type IconComponent`.

- [ ] Steps: failing story play tests (Button: Enter and Space fire `onClick`, disabled never fires, `isLoading` sets `aria-busy` and blocks clicks; IconButton: accessible name equals `aria-label`; Tooltip: shows on focus, hides on Escape) → run `test:stories` → FAIL → implement → PASS → commit `feat(design-system): add actions, badges and display primitives`.

### Task 6: Form controls and overlays

**Files:** `src/design-system/src/components/{TextField,TextArea,CheckBox,Switch,Select,ModalDialog,AlertDialog,DropdownMenu,Drawer}/…`

**Interfaces:**
- Field anatomy (Serendie TextField): `label: string`, `description?: string`, `invalid?: boolean`, `invalidMessage?: string`, `required?: boolean`; label wired with `htmlFor`, description and message via `aria-describedby`, `aria-invalid` when invalid. `TextField` wraps `input`, `TextArea` wraps `textarea`.
- `CheckBox` (`label`, `checked`, `onCheckedChange`), `Switch` (same), `Select` (`label`, `items: { value: string; label: string }[]`, `value`, `onValueChange`, `placeholder`, field props).
- `ModalDialog`: `isOpen`, `onOpenChange`, `title`, `description?`, `children`, `footer?: ReactNode`; full-screen sheet below 768px. `AlertDialog`: same shape, Radix AlertDialog, for destructive confirmations.
- `DropdownMenu` parts: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuRadioGroup`, `DropdownMenuRadioItem`, `DropdownMenuSeparator`.
- `Drawer`: `isOpen`, `onOpenChange`, `side?: "left" | "right"` (default right, as Serendie), `title` (visually hidden allowed), `children`.

- [ ] Steps: failing play tests — TextField: label click focuses input, invalid sets `aria-invalid` and announces the message; CheckBox/Switch: Space toggles; Select: Enter opens, arrows move, Enter selects, Escape closes and focus returns; ModalDialog/AlertDialog/Drawer: open from a trigger, focus moves inside, Tab stays inside, Escape closes, focus returns to trigger; DropdownMenu: arrows and Enter. Review Focus 5: a story opens `ModalDialog`, switches the theme global to `kurikawa`, and asserts the dialog surface's computed background equals the KURIKAWA `surface` value → run → FAIL → implement → PASS → commit `feat(design-system): add form controls and overlays`.

### Task 7: Navigation and app shell

**Files:** `src/design-system/src/components/{TopAppBar,SideNavigation,Breadcrumbs,Tabs,List,TitleBar,ThemePicker,AppLayout}/…`

**Interfaces:**
- `TopAppBar`: `title: ReactNode`, `headingIconButton?: ReactNode`, `trailingItems?: ReactNode`; sticky, `surface` background, bottom `outline` border.
- `SideNavigation`: `items: { href: string; label: string; icon: IconComponent; isActive: boolean }[]`, `renderLink(item, children): ReactNode` (lets the console use React Router's `Link`), `onNavigate?: () => void`; `nav` with `aria-label="Main"`, active item `aria-current="page"`.
- `Breadcrumbs`: `items: { label: string; href?: string }[]`, `renderLink`, last item `aria-current="page"`; long labels truncate with the full text in `title`.
- `Tabs` parts (`Tabs`, `TabList`, `TabItem`, `TabPanel`) over Radix Tabs; `TabList` scrolls horizontally when it overflows.
- `List`, `ListItem` (Serendie anatomy, used by the Drawer navigation).
- `TitleBar`: `breadcrumbs?: ReactNode`, `title: ReactNode`, `actions?: ReactNode`, `overflowActions?: { label: string; onSelect(): void; destructive?: boolean }[]`; below 768px `actions` collapse into an IconButton DropdownMenu built from `overflowActions` when given.
- `ThemePicker`: DropdownMenu radio group over `THEMES` using `useTheme`; trigger labelled "Colour theme: <label>".
- `AppLayout`: `productName: string`, `navigation: SideNavigationProps`, `trailingItems?: ReactNode`, `children`; ≥ 768px: TopAppBar over a persistent sidebar (width 224px) and `main`; < 768px: a menu `IconButton` in the TopAppBar opens a left `Drawer` holding the navigation; navigating closes it and focuses `main` (`tabIndex={-1}`).

- [ ] Steps: failing play tests — SideNavigation: Tab through items, `aria-current` on the active one; Tabs: arrows move, Home/End jump; ThemePicker: choose Asagi by keyboard → `<html data-panda-theme="asagi">`; AppLayout at `phone` (Review Focus 4): menu button opens Drawer, Escape closes and focuses the menu button, choosing a link closes it and focuses `main`; TitleBar at `phone` with a 60-character title and breadcrumbs (Review Focus 2) → `expectNoHorizontalPageScroll` → run → FAIL → implement → PASS → commit `feat(design-system): add navigation and the app layout`.

### Task 8: Data display

**Files:** `src/design-system/src/components/{Table,DataTable,Panel,Banner,EmptyState,ChartContainer}/…`, `src/design-system/package.json` (`@tanstack/react-table` 9.3.1, `recharts` 3.8.0 as peer deps)

**Interfaces:**
- `Table` parts (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) for hand-built tables; rows `min-h-row`, numeric cells accept `numeric` prop → right-aligned `tabular-nums`.
- `DataTable<T>`: `columns: ColumnDef<T>[]`, `data: T[]`, `getRowId?`, `initialSorting?`, `emptyState?: ReactNode`, `caption: string` (visually hidden); sortable headers are buttons with `aria-sort`; the table sits in a container with `overflow-x: auto`; first column `position: sticky; left: 0` with a `surface` background.
- `Panel`: `title?: ReactNode`, `actions?: ReactNode`, `children`; `surface-container` background, `outline` border, radius `--radius-lg`, no shadow.
- `Banner`: `type: "information" | "notice" | "negative" | "positive"`, `title`, `children`; `role="status"`, or `role="alert"` for `negative`.
- `EmptyState`: `title`, `description?`, `action?`.
- `ChartContainer`: wraps Recharts' `ResponsiveContainer`, exposes `CHART_COLOURS` (`var(--color-chart-1)` …) for series.

- [ ] Steps: failing play tests — DataTable: Enter on a header toggles sort and `aria-sort`; at `phone` with 12 columns (Review Focus 3) the scroll container's `scrollWidth > clientWidth`, `expectNoHorizontalPageScroll` passes, and the first cell's computed `position` is `sticky`; Banner `negative` has `role="alert"` → run → FAIL → implement → PASS → commit `feat(design-system): add tables, panels, banners and charts`.

---

### Task 9: Console on the design-system foundation and shell

**Files:**
- Modify: `src/data-platform/frontend/package.json` (add `@retail-lakehouse/design-system`, remove `@fontsource-variable/geist*`), `src/main.tsx`, `src/App.tsx`, `src/styles/globals.css`, `index.html`, `src/components/AppShell.tsx`, `src/components/AppShell.test.tsx`
- Delete: `src/theme/**`, `src/components/ThemeSwitch.tsx`, `src/components/ThemeSwitch.test.tsx`
- Create: `src/indexHtmlThemeBoot.test.ts`

**Interfaces:**
- Consumes: `ThemeProvider`, `THEME_STORAGE_KEY`, `THEMES`, `AppLayout`, `ThemePicker`, `TooltipProvider`, icons (Tasks 3, 5, 7).
- Produces: `globals.css` = `@import "@retail-lakehouse/design-system/styles.css";` plus `@source "../"` for console files plus a **temporary alias block** in `@theme inline` mapping every old shadcn colour name the console still uses (`background`, `foreground`, `card`, `muted`, `muted-foreground`, `primary`, `primary-foreground`, `secondary`, `accent`, `destructive`, `warning`, `success`, `border`, `input`, `ring`, `popover`, `chart-1..5`, `sidebar*`) to the nearest `--ds-*` token (`destructive → negative-text`, `warning → notice-text`, `success → positive-text`). Removed in Task 12. The `.dark` variant is gone.

- [ ] **Step 1: Write the failing test** `indexHtmlThemeBoot.test.ts`: read `index.html` raw; assert the boot script reads `localStorage` key `THEME_STORAGE_KEY`, sets `data-panda-theme` only for `asagi` and `kurikawa`, and contains no `"dark"`. Update `AppShell.test.tsx` to expect the TopAppBar product name, the sidebar `nav[aria-label="Main"]` with the four items, and a "Colour theme" button. Run `npm --prefix …/frontend test -- --run src/indexHtmlThemeBoot.test.ts src/components/AppShell.test.tsx` → FAIL.
- [ ] **Step 2: Implement** — `AppShell` becomes a thin console wrapper around `AppLayout` (nav items, React Router `Link` via `renderLink`, `ThemePicker` in `trailingItems`); `App.tsx` uses the design-system `ThemeProvider` and `TooltipProvider`; `index.html` boot script per the test.
- [ ] **Step 3: Verify** — console `test -- --run`, `lint`, `typecheck`, `build` all pass; `task --dir /Users/kcl/Projects/retail-lakehouse pre-pr` green; start `npm --prefix …/frontend run dev` and screenshot one page per theme at desktop and phone widths for the task report.
- [ ] **Step 4: Commit** `feat(console): move the console onto the design system shell and themes`

### Task 10: Forms and dialogs on design-system components

**Files:** `src/data-platform/frontend/src/components/forms/**`, `ConfirmDeleteDialog.tsx`, `RunMaintenanceDialog.tsx`, `ActionsMenu.tsx`, `SettingsForm.tsx`, `SettingsFieldGroup.tsx` and their tests.

- Replace `@/components/ui/{input,textarea,label,select,checkbox,switch,dialog,alert-dialog,dropdown-menu,button}` with `TextField`, `TextArea`, `Select`, `CheckBox`, `Switch`, `ModalDialog`, `AlertDialog`, `DropdownMenu`, `Button`, `IconButton`. The console's own `forms/TextField.tsx` and `SelectField.tsx` either disappear (callers use the design-system field directly) or shrink to domain wiring; `FormDialog` lays fields in one column below 768px.
- `ConfirmDeleteDialog` keeps its wording and type-the-name rule on `AlertDialog`.
- [ ] Steps: update the affected tests' selectors first (they still assert the same behaviour) and run them → FAIL against old markup → migrate → console tests PASS → `pre-pr` green → commit `refactor(console): build forms and dialogs from design-system components`.

### Task 11: Pages, panels and tabs on design-system components

**Files:** `src/data-platform/frontend/src/pages/**`, `src/components/{PageHeader,TableHeader,Breadcrumbs,ResourceListPage,ResourceSection,Panel,PanelSkeleton,StatusBadge,RunStatusBadge,HealthPanel,FreshnessPanel,LastRunPanel,MaintenancePanels,MaintenanceEmptyState,PropertiesPanel,RecentCommitsPanel,SchemaFieldsPanel,StoragePanel,CatalogDetails,CatalogObjectNotFound}.tsx`, `src/components/tabs/**`, and their tests.

- `PageHeader` and `TableHeader` render `TitleBar` (with `overflowActions` from the object's actions); console `Breadcrumbs` builds `items` for the design-system `Breadcrumbs`; console `Panel`/`PanelSkeleton` are replaced by design-system `Panel`/`Skeleton`; `StatusBadge`/`RunStatusBadge` map run states to design-system `StatusBadge` (`succeeded → positive`, `failed`/error `→ negative`, due/truncated `→ notice`, everything else `neutral`); lists and tab tables use `DataTable` (or `Table` where rows are not data records); alerts become `Banner`; empty states use `EmptyState`; charts use `ChartContainer`; icons come from the design system.
- [ ] **Step 1: Write the failing test** `src/pages/TablePage.mobile.test.tsx` (Review Focus 2): render the table page for a table named with 60 characters at `window.innerWidth = 390` and assert the title element has the design-system truncation class and the full name in `title`. Update the other tests' selectors. Run → FAIL.
- [ ] **Step 2: Migrate** page by page; after each page run its test file.
- [ ] **Step 3: Verify** — console tests, lint, typecheck, build pass; `pre-pr` green; screenshots of the table page and namespace page per theme at desktop and phone widths in the task report.
- [ ] **Step 4: Commit** `refactor(console): build pages, panels and tabs from design-system components`

### Task 12: Remove the old UI layer, guard the boundary, document

**Files:**
- Delete: `src/data-platform/frontend/src/components/ui/**`, `src/data-platform/frontend/components.json`, `src/data-platform/frontend/src/lib/utils.ts` (callers use `cn` from the design system)
- Modify: console `package.json` (remove `lucide-react`, `radix-ui`, `class-variance-authority`, `cn`, `shadcn`, `tw-animate-css`, `@tanstack/react-table` if unused directly), `src/styles/globals.css` (alias block removed), `vite.config.ts` (radix chunk group removed), `src/test/noRawColors.test.ts` → `src/test/designSystemBoundary.test.ts`
- Create: `src/design-system/CLAUDE.md`, `docs/adr/0008-design-system-on-serendie-tokens.md`
- Modify: `src/data-platform/frontend/CLAUDE.md`, root `CLAUDE.md` (topic table row for `src/design-system/CLAUDE.md`), `docs/agents/project-history.md`, `docs/agents/known-follow-ups.md`

- [ ] **Step 1: Write the failing test** `designSystemBoundary.test.ts` over every non-test source under `src/` (globbed raw): no raw hex, arbitrary colours or Tailwind palette colours (keep the current regexes); no `--sd-`; no imports from `radix-ui`, `@radix-ui/`, `lucide-react`, `@serendie/`; design-system imports only from `@retail-lakehouse/design-system` (no deep paths); no old shadcn colour utilities (`bg-background`, `text-muted-foreground`, `bg-card`, `text-destructive`, `border-border`, …). Run → FAIL on remaining offenders.
- [ ] **Step 2: Remove** the leftovers until the test passes; delete the alias block.
- [ ] **Step 3: Document** — ADR 0008 (context, decision: Serendie tokens + docs as spec, components on Radix + Tailwind 4, no `@serendie/ui`; consequences); `src/design-system/CLAUDE.md` (layers, naming, window classes, status-colour rule, story and keyboard-test requirements, how to add a component); console `CLAUDE.md` rewritten to "build pages from `@retail-lakehouse/design-system`; domain components stay here"; project-history line for 2026-11-08; follow-ups: keyboard shortcuts and command palette, visual regression, the `konjo-dark` theme if dark mode returns.
- [ ] **Step 4: Verify** — `task --dir /Users/kcl/Projects/retail-lakehouse pre-pr` green; `docker build --file /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend/Dockerfile /Users/kcl/Projects/retail-lakehouse` succeeds; `rg -n "lucide-react|radix-ui" /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend/src` is empty.
- [ ] **Step 5: Commit** `refactor(console): drop the shadcn layer and guard the design-system boundary` (code) and `docs(design-system): record the design-system decision and rules` (docs).
