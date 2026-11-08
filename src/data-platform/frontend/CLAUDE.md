# Console UI

Rules for `src/data-platform/frontend` pages. **Build pages from `@retail-lakehouse/design-system` (rules in `src/design-system/CLAUDE.md`); domain components stay here.**

- **Import the design system only from `@retail-lakehouse/design-system`.** No deep paths, `radix-ui`, `@radix-ui/*`, `lucide-react` or `@serendie/*`. Icons come from the design system.
- **A missing component goes to the design system**, with its story and keyboard test, not into the console. Domain components (`MaintenancePanels`, `MaintenanceGate`, `ConfirmDeleteDialog`'s wording, `ActionsMenu`) stay here, built from design-system parts.
- **Semantic utilities only** (`bg-surface`, `text-on-surface-variant`, `border-outline`, `text-negative-text`). No raw hex, arbitrary or Tailwind palette colours, no `--sd-*`, no old shadcn names (`bg-background`, `text-muted-foreground`, `border-border`), no `dark:`. Enforced by `src/test/designSystemBoundary.test.ts`.
- **Status colours only for status.** Not due, cooldown and disabled stay neutral; notice = due operation or truncated count; negative = error or failed run; positive = succeeded run only. Use `StatusBadge`; bare status text uses `negative-text`, `positive-text`, `notice-text`.
- **Theme colour for interaction, as Serendie does** (rules in `src/design-system/CLAUDE.md`, Colour use). Every text link is a `TextLink` wrapping the router `Link` (`asChild`), with `inline` inside a sentence; never style a `Link` by hand.
- **Identifiers in `font-mono`** (procedure names, snapshot ids, file paths, `execution_ref`, property keys / values, schema types); `tabular-nums` on number columns; sentence case, no all-caps labels.
- **Columns come from `createDataTableColumnHelper`** and render through `DataTable`; `@tanstack/react-table` is imported here for types only.
- **Phones count.** Every page works at phone width: no horizontal page scroll, tables scroll inside their container.

## Catalog pages

Catalog pages (spec `docs/superpowers/specs/2026-11-07-catalog-context-design.md`) follow one pattern, so every object type looks the same:

- **Every page starts with a header (`PageHeader`, or `TableHeader` on the table page):** `Breadcrumbs` built from `lib/catalogPaths.ts` (Catalogs → catalog → namespace → object), the title, and the object's `ActionsMenu` beside it (Edit / Rename / Delete where Polaris allows them; views and generic tables hold Delete only).
- **List pages use `ResourceListPage`** (Catalogs, catalog, namespace): the header, then a list with its New button and per-row delete. The namespace page lists tables, views and generic tables in one list with a Type column.
- **Every delete uses `ConfirmDeleteDialog`:** it names the object and its full path, enables Delete only after the user types the name, and shows Polaris's error (a non-empty catalog or namespace is refused, never cascaded). A page that deletes or renames the object it shows calls `useLeavingPage` so its queries stop before it navigates away.
- **The table page joins two APIs:** the catalog API for the header, the Overview summary and the Schema, Snapshots and Properties tabs, and the maintenance API for the maintenance panels and the Commits, Maintenance and Settings tabs. A table maintenance does not manage shows `MaintenanceEmptyState` with its reason (catalog not covered, no discovery rule, excluded, dropped), through `MaintenanceGate`.
- **URLs carry names, not ids.** A namespace segment is its parts joined by U+001F and sent as `%1F` (`apiNamespace`), so a part containing a dot round-trips. After every write, failed or not, the page refetches from the API (invalidate in `onSettled`, since a write can fail after part of it landed); it never patches local state.
