# Console UI

Rules for `src/data-platform/frontend` pages (spec `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`):

- **Build from `components/ui/` primitives.** Add a missing primitive with the shadcn CLI rather than hand-rolling one.
- **Token classes only.** Use tokens via Tailwind classes (`bg-background`, `text-muted-foreground`, `border-border`); no raw hex values or arbitrary colour classes (`[#…]`) in feature code (`src/components/` except `ui/`, `src/pages/`). Enforced by `src/test/noRawColors.test.ts`.
- **Colour only for status.** Neutral for everything else (including not due, cooldown, disabled); `warning` = due operation or truncated count; `destructive` = error or failed run; `success` = succeeded run only.
- **Identifiers in Geist Mono** (procedure names, snapshot ids, file paths, `execution_ref`, property keys / values, schema types); `tabular-nums` on number columns; sentence case, no all-caps labels.
- **No shadows on panels** (one subtle shadow on overlays only), no gradients, no entrance animations.

## Catalog pages

Catalog pages (spec `docs/superpowers/specs/2026-11-07-catalog-context-design.md`) follow one pattern, so every object type looks the same:

- **Every page starts with a header (`PageHeader`, or `TableHeader` on the table page):** `Breadcrumbs` built from `lib/catalogPaths.ts` (Catalogs → catalog → namespace → object), the title, and the object's `ActionsMenu` beside it (Edit / Rename / Delete where Polaris allows them; views and generic tables hold Delete only).
- **List pages use `ResourceListPage`** (Catalogs, catalog, namespace): the header, then a list with its New button and per-row delete. The namespace page lists tables, views and generic tables in one list with a Type column.
- **Every delete uses `ConfirmDeleteDialog`:** it names the object and its full path, enables Delete only after the user types the name, and shows Polaris's error (a non-empty catalog or namespace is refused, never cascaded). A page that deletes or renames the object it shows calls `useLeavingPage` so its queries stop before it navigates away.
- **The table page joins two APIs:** the catalog API for the header, the Overview summary and the Schema, Snapshots and Properties tabs, and the maintenance API for the maintenance panels and the Commits, Maintenance and Settings tabs. A table maintenance does not manage shows `MaintenanceEmptyState` with its reason (catalog not covered, no discovery rule, excluded, dropped), through `MaintenanceGate`.
- **URLs carry names, not ids.** A namespace segment is its parts joined by U+001F and sent as `%1F` (`apiNamespace`), so a part containing a dot round-trips. After every write the page refetches from the API; it never patches local state.
