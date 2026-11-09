# Design system

Rules for `src/design-system` (`@retail-lakehouse/design-system`, spec `docs/superpowers/specs/2026-11-08-design-system-design.md`, ADR `docs/adr/0008-design-system-on-serendie-tokens.md`). Every UI in the repo is built from it; the console is its first consumer.

## Layers

- **Serendie tokens** (`--sd-*`, from `@serendie/design-token`) → **semantic tokens** (`--ds-*` in `src/styles/semantic.css`, listed in `src/tokens/semanticTokens.ts`) → **Tailwind utilities** via `@theme` in `src/styles/index.css` (`bg-surface`, `text-on-surface-variant`, `border-outline`, …).
- Only this package reads `--sd-*`. Components use utilities, never `--sd-*`, raw hex or Tailwind palette colours.
- Colours, radii, borders and states come from Serendie values only. Never derive a colour.
- Themes: KONJO (default, no attribute), ASAGI (`data-panda-theme="asagi"`), KURIKAWA (`data-panda-theme="kurikawa"`) on `<html>`, light values only. No dark mode. Adding a semantic token means defining it for all three themes (`themeTokens.test.ts` fails otherwise).

## Components

- **Stack:** Radix (`radix-ui`) for behaviour, Tailwind 4 for style, `cva` for variants, `cn` for class merging. Tables use TanStack Table. Icons only from Tabler (`@tabler/icons-react`, pinned), re-exported by name from `src/icons` with a default 1.5 stroke (`withDefaultStroke`; add an icon there before using it). Calendars use `react-day-picker` (pinned), styled with the semantic utilities instead of its stylesheet. No `@serendie/symbols`, `@serendie/ui`, Ark UI, Panda CSS or `lucide-react`.
- **Names:** Serendie's name where Serendie has the component (`Button`, `IconButton`, `Badge`, `Divider`, `TextField`, `TextArea`, `CheckBox`, `Switch`, `Select`, `ModalDialog`, `DropdownMenu`, `Tooltip`, `DatePicker`, `Drawer`, `TopAppBar`, `Breadcrumbs`, `Tabs`, `List`, `DataTable`, `Banner`). A plain name where it has none (`AlertDialog`, `SideNavigation`, `TitleBar`, `AppLayout`, `Panel`, `EmptyState`, `Skeleton`, `StatusBadge`, `ThemePicker`, `ChartContainer`, `Table`, `TextLink`).
- **Layout:** one folder per component under `src/components/<Name>/` holding `<Name>.tsx` and `<Name>.stories.tsx`. Export it, and its props type, from `src/index.ts`. The console imports only from `@retail-lakehouse/design-system`, never a deep path.
- **Inventory is what the console needs**, not all of Serendie. Domain components (maintenance panels, delete-confirm wording) stay in the console.
- **Ported Serendie values or source** keep the MIT notice in a header comment naming `serendie/serendie` and the file. Never bundle `SerendieOfficeVF`. No Serendie or Mitsubishi Electric names or logos in product UI; the README carries the credit line.

## Window classes

- Split at 768px (`--sd-system-dimension-breakpoint-expanded`). Below it: Serendie `*_compact` typography and touch sizes, targets at least 44 x 44px. At or above it: `*_expanded` typography and dense sizes.
- Expanded controls (buttons, inputs, selects, nav items) are 36px high and table rows 36px. Compact controls and rows are 44px. `@media (pointer: coarse)` keeps 44px at any width.
- Use the `type-*` utilities from `src/styles/typography.css` and the density utilities from `src/styles/density.css`; do not set font sizes by hand.
- Each story records a component's expanded sizes as a documented departure from Serendie.

## Colour use

Follow Serendie's components: read the component's source in `serendie/serendie` (`src/components/<Name>/`) and use the same token for the same part. The theme colour carries interaction and selection; the status colours carry status only.

- **Links and selected or active states use the theme colour:** `text-primary` for links (`TextLink`, `Breadcrumbs`) and the active tab; `bg-selected-surface` with `text-on-surface` for a selected list item or nav item (its icon `text-primary`); `bg-inverse-primary` for table headers and expanded or selected rows; `bg-primary-container` for filled buttons, checked check boxes and switches.
- **Hover is `bg-hovered-variant`** on a surface and `bg-hovered` over a filled control. Never a derived colour such as `bg-on-surface/5`.
- **Overlays:** menus and select lists on `bg-surface-container-bright`, tooltips `bg-inverse-surface` with `text-inverse-on-surface`.
- **Where we depart from Serendie for contrast:** secondary text on `selected-surface` is `text-on-surface`, not `on-surface-variant` (about 3.3:1); control borders use `outline-dim`, not `outline`.
- **Status:** badges use `{positive|notice|negative}Container` with its `on…Container` text (`StatusBadge`, `Badge`). Bare status text or an icon on a surface uses `negative-text`, `positive-text` (`chart-mark-positive-05`) or `notice-text` (`chart-mark-notice-05`). `positive` and `notice` are never text or icon colours on a surface, and status colours never mean anything but status.

## Accessibility and tests

- Contrast floor in every theme: 4.5:1 text, 3:1 large text and UI parts (input borders, focus ring, icons). `contrastRatio.test.ts` and `themeTokens.test.ts` enforce it over the semantic token pairs.
- Control boundaries (field, check box and outlined button borders, the unchecked switch track) use `outline-dim`, which meets 3:1. `outline` is only for decorative dividers and panel edges.
- **Every component state has a story** with a theme switcher toolbar and axe; an axe violation fails `task checks:component-test`.
- **Every interactive component has a keyboard play function:** Tab order, a visible focus ring, open and close with Enter, Space and Escape, focus returning to the trigger, and arrow keys in menus, selects, tabs and the sidebar.
- Stories also check there is no horizontal page scroll at phone width (`expectNoHorizontalPageScroll`).
- Unit tests: `npm --prefix src/design-system test -- --run`. Stories as browser tests: `npm --prefix src/design-system run test:stories` (needs `npx playwright install chromium`).

## Add a component

1. Check Serendie's docs for the component; use its name and anatomy, or a plain name if it has none.
2. Write the story first, with a play function for keyboard and focus behaviour. Run it and watch it fail.
3. Build `<Name>.tsx` on the Radix primitive (or a native element) with Tailwind semantic utilities and the density utilities.
4. Export it from `src/index.ts`.
5. Run lint, typecheck, unit tests and story tests (`task pre-pr` covers them).
