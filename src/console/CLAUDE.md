# Console UI

Rules for `src/console` pages (spec `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`):

- **Build from `components/ui/` primitives.** Add a missing primitive with the shadcn CLI rather than hand-rolling one.
- **Token classes only.** Use tokens via Tailwind classes (`bg-background`, `text-muted-foreground`, `border-border`); no raw hex values or arbitrary colour classes (`[#…]`) in feature code (`src/components/` except `ui/`, `src/pages/`). Enforced by `src/test/noRawColors.test.ts`.
- **Colour only for status.** Neutral for everything else (including not due, cooldown, disabled); `warning` = due operation or truncated count; `destructive` = error or failed run; `success` = succeeded run only.
- **Identifiers in Geist Mono** (procedure names, snapshot ids, file paths, `execution_ref`, property keys / values, schema types); `tabular-nums` on number columns; sentence case, no all-caps labels.
- **No shadows on panels** (one subtle shadow on overlays only), no gradients, no entrance animations.
