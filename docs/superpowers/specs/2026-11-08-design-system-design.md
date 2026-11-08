# Design system — design

Date: 2026-11-08. Supersedes the visual rules of `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`
(monochrome look, light/dark mode, "colour only for status", no shadows). The console's features and behaviour from
`docs/superpowers/specs/2026-10-31-data-platform-console-design.md` and the catalog spec stay as they are.

## Intent

The console works, but its UI is a set of shadcn primitives styled page by page. The owner wants front-end work to be
systematic and to scale: one design system, owned in this repo, that every page is built from. They chose the visual
language of Serendie, Mitsubishi Electric's open-source design system (MIT), for its Japanese traditional colour
themes, and decided to **build the components themselves on Tailwind CSS 4 + Radix, using Serendie's design tokens
and treating Serendie's component docs as the design spec.** Serendie's own React library (`@serendie/ui`, Ark UI +
Panda CSS) is not adopted: it would bring a second headless stack and a second styling engine, it lacks the
command palette / combobox the keyboard goal needs, and it would tie the console to a fast-moving library with a small
community.

Two long-term goals shape every decision here, though only their foundations land now: **the whole console will be
operable from the keyboard with shortcuts**, and **users pick among several colour themes**.

Success, in the owner's words: open the console and every page shows the design system's look, built entirely from
modular components, and the user can switch between the KONJO, ASAGI and KURIKAWA colour themes.

## Goals

- A design system package at `src/design-system/`, separate from the console so other front ends can use it later.
- Serendie design tokens (`@serendie/design-token`) as the single source of colour, typography, spacing, radius and
  elevation.
- Three selectable colour themes: **KONJO** (default), **ASAGI**, **KURIKAWA**, using Serendie's light values only.
- Components built on Radix primitives and Tailwind 4, styled to Serendie's component docs.
- The console fully migrated: a new app shell and every page built from design-system components.
- **Usable on phones and desktops alike** (owner's requirement): every page works at phone width with touch, and stays
  dense and efficient on a desktop.
- Keyboard foundations: every interactive component is fully keyboard-operable, with tests proving it.
- Storybook as the design system's living catalogue, with automated accessibility checks.

## Non-goals

- **No dark mode.** The user chooses a colour theme, not theme × light/dark. The current dark mode is removed.
- No SUMIRE or TSUTSUJI themes, and no colours derived by us: only values Serendie ships.
- No keyboard shortcuts, shortcut registry or command palette yet (next phase).
- No visual regression testing yet (next phase, once components are stable).
- No publishing to npm or version numbers; the package is consumed inside this monorepo.
- No `@serendie/ui`, Ark UI or Panda CSS in the dependency tree.
- No change to routes, API calls, data flow or what each page does.
- No i18n.

## Anti-goals

- Two headless component stacks, or two styling engines.
- Console code (pages, feature components) reading `--sd-*` variables, writing raw colours, or importing Radix
  directly. If a page needs something the design system lacks, the design system gains it.
- A theme that fails contrast: a theme ships only if its tests pass.
- Presenting the console as a Serendie or Mitsubishi Electric product.

## Constraints

- **Stack is fixed:** React 19, Vite 8, TypeScript, Tailwind CSS 4, Radix (`radix-ui`), TanStack Query/Table/Router
  as the console uses today. Dependencies pinned to exact versions, as the console does now.
- **Licensing:** Serendie packages are MIT; installed from npm, their `LICENSE` travels with them. Any Serendie source
  we port (recipe values, SVGs) keeps the MIT notice and names its origin. Do not bundle `SerendieOfficeVF` (no licence
  found). The repo is AGPL-3.0; MIT code inside it is fine. Credit: "Uses Serendie design tokens and symbols (MIT,
  Mitsubishi Electric)" in the design system README; no Serendie or Mitsubishi Electric logos or names in the product
  UI.
- **Accessibility floor:** WCAG 2.2 AA contrast for text and UI in every shipped theme; full keyboard operation of every
  interactive component.
- Existing console behaviour tests keep passing; they may change selectors or setup where the markup changed, never
  what they assert about behaviour.

## What the owner decided

### Package and repo layout

- `src/design-system/` is its own package (e.g. `@retail-lakehouse/design-system`, private), linked to the console with
  **npm workspaces** declared in the repo-root `package.json`. One root lockfile replaces
  `src/data-platform/frontend/package-lock.json`.
- The console consumes the design system as TypeScript source (no build step for the package); the design system's CSS
  entry declares Tailwind `@source` for its own files so its classes are generated.
- The console image build must now see both folders: the Dockerfile's build context and `source_tag` in
  `platform/25-lakehouse-control-plane/build.sh` must cover `src/design-system/` as well, so a design-system change
  rebuilds and retags the console image.

### Tokens and themes

- Three layers: **Serendie tokens** (`--sd-*`, from `@serendie/design-token/tokens.css`) → **design-system semantic
  tokens** (names the design system owns) → **Tailwind utilities** via `@theme`. Only the design system reads `--sd-*`.
- Themes switch with Serendie's own mechanism: KONJO is the default (no attribute); ASAGI and KURIKAWA set
  `data-panda-theme="asagi" | "kurikawa"` on `<html>`.
- The chosen theme persists in `localStorage` and is applied before first paint (no flash of the default theme).
- Status colours map to Serendie's impression roles: success → `positive`, error/failed → `negative`,
  warning/due → `notice`. *Builder's call (owner delegated it, asking only that it look good and read easily):*
  status badges use the role's container with its on-container text (`positiveContainer` / `onPositiveContainer`, and
  the same for `notice` and `negative`), which pass AA in all three themes. A status shown as bare text or an icon on
  a surface uses a Serendie-shipped shade that passes: `negative` (5.6:1 on white), `chart-mark-positive-05`
  `#2C7C60` (5.05:1) for success, `chart-mark-notice-05` `#816E00` (5.04:1) for warning. `positive` (`#2EAB80`, 2.9:1)
  and `notice` (`#DEC400`, 1.75:1) are never used as text or icon colours on a surface. No colour is derived by us.
- Charts keep Recharts, coloured from Serendie's chart tokens.

### Typography and icons

- **Noto Sans** for text and **Noto Sans Mono** for identifiers and code (self-hosted via Fontsource, as Geist is
  today).

### Density: follow Serendie's two window classes

*Builder's call, from the owner's requirement that the console work on phones and desktops.* Serendie defines two
window classes split at `--sd-system-dimension-breakpoint-expanded` (768px), each with its own type scale. The design
system follows the same split for type **and** sizing:

| Window class | Width | Type scale | Control and row sizing |
|---|---|---|---|
| `compact` (phones, narrow windows) | < 768px | Serendie `*_compact` (body 16px) | Serendie's touch sizes; touch targets at least 44 × 44px |
| `expanded` (tablets in landscape, desktops) | ≥ 768px | Serendie `*_expanded` (body 14px) | Dense desktop sizing (controls and table rows around 32–36px) |

A coarse pointer (`@media (pointer: coarse)`) keeps the 44px touch-target minimum even in the `expanded` class.
Colours, radii, borders, states and proportions follow Serendie in both classes; only heights and paddings differ in
`expanded`, and each component's story records its `expanded` sizes as a documented departure from Serendie.

On phones: the sidebar becomes the Drawer, title-bar actions that do not fit move into an overflow menu, forms stack
to one column, and data tables scroll horizontally inside their own container (first column sticky) rather than
widening the page.
- **`@serendie/symbols` replaces `lucide-react` everywhere.** The console gets icons through the design system, not by
  importing the icon package directly.

### App shell and navigation (owner picked layout C)

- A **TopAppBar** across the top: product name on the left, the **theme picker** on the right.
- A **persistent left sidebar** below it holding the primary navigation (Tables, Catalog, Presets, Discovery rules),
  with the current page marked. Serendie specifies no desktop sidebar, so the design system defines it in Serendie's
  visual language and documents it.
- Narrow screens collapse the sidebar into a left **Drawer** opened from a menu button in the TopAppBar.
- Each page starts with a **title bar**: Breadcrumbs, the page title, and the page's actions. In-page sections (the
  table page's tabs) use **Tabs**.

### Components

- The inventory is **what the console needs**, not everything Serendie has: the primitives in today's
  `components/ui/`, the shell pieces above, and the generic patterns the console repeats (panels/cards, status badge,
  data table, empty state, skeleton). Domain components (`MaintenancePanels`, `ConfirmDeleteDialog`'s wording,
  `MaintenanceGate`, …) stay in the console, rebuilt from design-system parts.
- Where Serendie has an equivalent, the design system uses **Serendie's component name and anatomy** (e.g.
  `ModalDialog`, `TextField`, `Divider`, `Banner`, `DataTable`, `TopAppBar`, `Drawer`). Behaviour comes from the matching
  Radix primitive; tables from TanStack Table (the console's existing version).
- Serendie's docs site and the `@serendie/ui` source (recipes) are the design spec for sizes, states and spacing. Where
  Serendie is silent, the design system decides and records it in the component's story.

### Quality

- **Storybook** in `src/design-system/`, with a story for every component state, a theme switcher toolbar covering the
  three themes, and the a11y addon (axe).
- Stories run as tests in a real browser in the test suite: **axe violations fail the build**, and **interactive
  components carry keyboard interaction tests** (play functions): focus order, visible focus ring, open/close with
  Enter/Space/Escape, focus returning to the trigger, arrow-key movement in menus, selects, tabs and the sidebar.
- A plain unit test computes **WCAG contrast for every theme** over the semantic token pairs (text on surfaces, muted
  text, text on primary, status text on its container, focus ring on surface) and fails below AA (4.5:1 text, 3:1 large
  text and UI). A second test checks **every theme defines every semantic token**.
- A guard test keeps console code free of raw colours, `--sd-*` references and direct Radix / icon-package imports.
- New checks join the Taskfile test tasks so `task pre-pr` runs them.

### Documentation

- An ADR: adopt Serendie tokens and docs as the design spec; build components on Radix + Tailwind 4; do not adopt
  `@serendie/ui`.
- `src/design-system/CLAUDE.md` with the design system's rules; `src/data-platform/frontend/CLAUDE.md` rewritten
  against it; root `CLAUDE.md` topic table and `docs/agents/project-history.md` updated.
- `docs/agents/known-follow-ups.md` records the next phase: keyboard shortcuts and command palette, visual regression.

## Left to the builder

- Exact component APIs and props, file names inside the package, and the semantic token names.
- Storybook version (current stable) and how stories run as tests.
- Sidebar width and spacing values where Serendie is silent; the exact `expanded` heights within the range above.
- The order of the migration and how it is split into tasks and commits, provided every commit keeps the console
  working and `task pre-pr` green.
