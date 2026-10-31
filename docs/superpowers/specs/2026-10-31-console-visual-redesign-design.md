# Console visual redesign — design

Date: 2026-10-31. Builds on `docs/superpowers/specs/2026-10-31-data-platform-console-design.md` (the console's
features); this document changes only how the console looks and how its UI code is organised.

## Intent

The console (`src/console/`) works but is styled with one hand-written stylesheet. The owner is not a front-end
engineer or designer and wants the console to look polished, and to stay easy to extend — by Claude now and by other
front-end engineers later. So the UI layer moves onto popular, well-documented building blocks, with one set of
design rules that every future page follows.

## Goals

- A minimalist, monochrome look in the spirit of Vercel (the owner also likes Linear and Databricks): white, black and
  greys; colour only where something needs attention.
- Light and dark mode, both first-class.
- Mainstream stack that a hired front-end engineer recognises immediately: Tailwind CSS + shadcn/ui on the existing
  React + TypeScript + Vite app.
- Design tokens in one place; pages and feature components never hard-code colours, radii or spacing.
- Every current feature and behaviour stays exactly as it is.

## Non-goals

- No new pages or features (no presets, discovery rules or runs pages yet), no backend change.
- No Next.js: the console is an internal SPA served by nginx behind the gateway; SSR and server routes add a Node
  runtime and overlap FastAPI without helping this product.
- No Storybook yet (add it when several people build components).
- No marketing-style flourishes: no gradients, no decorative illustrations, no entrance animations.

## Anti-goals

- Looking like a generic template: identical rounded cards with soft shadows everywhere, all-caps eyebrow labels,
  gradient washes.
- A redesign that silently changes behaviour (a button that no longer does the same thing, a lost error or empty
  state, a lost not-in-catalog notice).
- Colour used as decoration, so that a real problem no longer stands out.

## Decided with the owner

- Direction B from the mockups: monochrome, Vercel-like (mockup kept at
  `.superpowers/brainstorm/68197-1793429489/content/style-directions.html`, git-ignored).
- Light and dark mode both supported.
- Stack: keep React + TypeScript + Vite + TanStack Query + react-router; add Tailwind CSS and shadcn/ui; charts with
  Recharts (shadcn's Chart); the table list with TanStack Table (shadcn's Data Table).
- Scope: restyle the table list and all five table tabs; functionality unchanged.

## Design (Claude's calls — the owner can override)

### Tokens

Colour tokens are CSS variables in one file (`src/console/src/styles/globals.css`) using shadcn's variable names
(`--background`, `--foreground`, `--card`, `--muted`, `--muted-foreground`, `--border`, `--primary`,
`--primary-foreground`, `--destructive`, …) plus two status tokens, `--warning` and `--success`.

| Token | Light | Dark | Use |
|---|---|---|---|
| background | `#ffffff` | `#000000` | page |
| surface (`--card`, sidebar) | `#fafafa` | `#0a0a0a` | sidebar, panel headers |
| border | `#ebebeb` | `#262626` | every hairline |
| foreground | `#171717` | `#ededed` | text |
| muted-foreground | `#666666` | `#a1a1a1` | secondary text |
| primary | `#000000` | `#ffffff` | primary buttons, active tab underline |
| warning | `#a35200` | `#ffb224` | a due operation, a truncated count |
| destructive | `#d93036` | `#ff6166` | errors, failed runs |
| success | `#297a3a` | `#62c073` | a succeeded run only |

Rules: neutral is the default for everything, including "not due", "cooldown" and "disabled"; `warning` marks a due
operation; `destructive` marks an error or failed run; `success` appears only on run outcomes. Both themes meet WCAG
AA contrast for text.

Radius: 6px for buttons and inputs, 8px for panels, full for status badges. Spacing on Tailwind's 4px scale. Shadows:
none on panels (borders do the work); one subtle shadow only on overlays (dialogs, popovers).

### Type

- Geist for all UI text; Geist Mono for real identifiers: operation procedure names (`rewrite_data_files`), snapshot
  ids, file paths, `execution_ref`, property keys and values, schema field types.
- Bundled with the app (`@fontsource-variable/geist`, `@fontsource-variable/geist-mono`), not loaded from Google
  Fonts, so the console works without internet access from the cluster.
- Scale: page title 24px / 600 / tight tracking; section titles 14px / 500; body 14px; secondary 13px; tabular numbers
  (`font-variant-numeric: tabular-nums`) in every number column.
- Sentence case everywhere; no all-caps labels.

### Layout

```
┌────────────┬─────────────────────────────────────────────┐
│ Lakehouse  │ iceberg / e2e                               │
│            │ tm_e2e_orders                 [Pause] [Run] │
│ Tables     │ (Active)  1,204,331 rows  15 files  3m ago  │
│            │ Overview  Commits  Maintenance  Properties  Settings
│            │ ─────────────────────────────────────────── │
│            │ ┌ Health ─────────────┐ ┌ Storage ─────────┐ │
│            │ │ rewrite_data_files  │ │ 48.2 MB current  │ │
│            │ │ …                   │ │ ▇▇▇▇▇▇▇░░░       │ │
│            │ └─────────────────────┘ └──────────────────┘ │
│ ◐ Theme    │ ┌ Freshness ──────────────────────────────┐ │
└────────────┴─────────────────────────────────────────────┘
```

- App shell: fixed narrow left sidebar (product name, a nav list that today holds only "Tables", theme switch at the
  bottom) and a left-aligned main column with a max width of about 1200px.
- Table list: a Data Table with sortable columns (name, status, selection, source preset, updated), the existing
  status filter and search above it, rows linking to the table page.
- Table page: breadcrumb (catalog / namespace), the table name as the page title, actions (Pause/Resume, Run
  maintenance) to the right, one meta line (status badge and key numbers), then underline tabs.
- Overview: Health and Storage side by side on wide screens, Freshness full width below, then schema / partition spec,
  recent commits and last run; one column below ~900px.
- Bordered panels with a title row, not shadowed cards; tables inside panels use hairline row dividers.
- Mobile (≥ 360px): sidebar collapses into a top bar with a menu sheet; tables scroll horizontally inside their
  panel, never the page.

### Components

- shadcn/ui primitives copied into `src/console/src/components/ui/` (Button, Badge, Tabs, Table, Dialog,
  AlertDialog, Input, Checkbox, Select, Switch, Label, Tooltip, Sheet, DropdownMenu, Skeleton, Alert, Chart, Separator).
  They are owned code and may be adjusted to the tokens.
- Feature components stay where they are (`components/`, `components/tabs/`, `pages/`) and are rebuilt on the
  primitives. Run maintenance and Reset to preset become real dialogs (Dialog / AlertDialog): focus moves in, Esc
  cancels, focus returns — this closes the earlier accessibility follow-up.
- Loading states use Skeleton rows; empty and error states keep their current wording.
- Icons: lucide-react (shadcn's default), used sparingly — only where an icon carries meaning (theme switch, menu,
  external link, row expand chevron).
- The Freshness chart moves from hand-written SVG to shadcn Chart (Recharts), stacked by operation in greys with the
  hover tooltip showing the hour and counts.

### Theme

- Default follows the operating system (`prefers-color-scheme`); the sidebar switch offers Light, Dark, System.
- The choice is stored in `localStorage` (wrapped in try/catch; failure falls back to System) and applied as the
  `dark` class on `<html>` before first paint (a tiny inline script in `index.html`) so the page never flashes the
  wrong theme.

### Tests

- All existing tests keep their behavioural assertions (requests sent, rows shown, notices, gating). Where markup
  changes break a selector, the selector changes, not the assertion; prefer role/label queries.
- New tests: the theme switch sets and persists the class; Run maintenance and Reset to preset open as dialogs and
  Esc cancels without sending a request.
- Console CHECKS (typecheck, lint, test, build) and the Docker build stay green; the deployed console passes the
  wave-25 `validate.sh`.

### Rules for future pages (go into CLAUDE.md)

- Build UI from `components/ui/` primitives; add a missing primitive with the shadcn CLI rather than hand-rolling one.
- Use tokens via Tailwind classes (`bg-background`, `text-muted-foreground`, `border-border`); no raw hex values or
  arbitrary colour classes in feature code.
- Colour only for status, with the meanings in the token table.
- Identifiers in Geist Mono; numbers tabular; sentence case.

### Settled after the builder check (Claude's calls)

- Table list columns are the ones the list already shows from `GET /v1/tables` (name, status, selection, source
  preset, updated) — no API change. Default sort is name ascending; clicking a header sorts by that column; sort
  state lives in component state, not the URL. The status filter and the search box stay as separate controls above
  the table.
- The table page's meta line uses the numbers the header already reads from `metadata` (rows, data files, bytes,
  average file size, snapshots, last commit); nothing new is fetched. The breadcrumb is plain text; "Tables" in the
  sidebar and the product name link back to the list.
- Tailwind CSS v4 with `@tailwindcss/vite` and CSS-first config. If a library's newest release does not support the
  console's pinned React / Vite / TypeScript, use the newest release that does and note it; do not downgrade React,
  Vite or TypeScript.
- Tests may change selectors and DOM structure when a Radix primitive replaces a hand-written element (for example a
  Select replacing a native select); the behavioural assertions stay. Add jsdom shims Radix and Recharts need
  (ResizeObserver, matchMedia, pointer capture, scrollIntoView) in `src/test/setup.ts`.
- Freshness chart: commit operations are few (append, overwrite, delete, replace); each gets its own grey step
  (darkest = append) in both themes, with a small legend under the chart; the hover tooltip lists counts per
  operation.
- nginx sends no Content-Security-Policy today, so the inline theme script is fine. If a CSP is added later, the
  script needs a hash.

## Left to the builder

- Exact Tailwind / shadcn / Recharts / TanStack Table / fontsource versions (exact pins, as the console already does).
- shadcn configuration details (`components.json`, path alias `@/`), lint rules for the new files.
- Breakpoint values and the exact sidebar width.
- Order of migration (shell first, then pages) and how many commits.
