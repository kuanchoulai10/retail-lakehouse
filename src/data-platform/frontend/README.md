# Data Platform Console

Web UI for table owners in front of the table-maintenance API. React + TypeScript, built
with Vite, tested with Vitest and Testing Library. Design:
`docs/superpowers/specs/2026-10-31-data-platform-console-design.md`.

The app is served under `/console/` and calls the API at `/console/api/v1/…`.

## UI

Styling is Tailwind CSS v4 (CSS-first config in `src/styles/globals.css`) with shadcn/ui
primitives in `src/components/ui/`; fonts are Geist and Geist Mono, bundled via fontsource.
Visual design: `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`.

- Build pages from `src/components/ui/` primitives; add a missing one with the shadcn CLI
  (`npx --prefix src/data-platform/frontend shadcn add <component>`) rather than hand-rolling it.
- Use token classes only (`bg-background`, `text-muted-foreground`, `border-border`, …): no raw
  hex values or `[#…]` arbitrary colours in `src/components/` (outside `ui/`) or `src/pages/`.
  `src/test/noRawColors.test.ts` fails on either.
- Colour only for status: `warning` = due operation or truncated count, `destructive` = error or
  failed run, `success` = succeeded run; everything else stays neutral.
- Identifiers in Geist Mono (`font-mono`), `tabular-nums` on number columns, sentence case.
- The theme (Light / Dark / System, default System) is stored in `localStorage` key
  `console-theme`; an inline script in `index.html` sets the `dark` class before first paint.

## Develop

```bash
npm --prefix src/data-platform/frontend install
npm --prefix src/data-platform/frontend run dev
```

The dev server proxies `/console/api/*` to `http://localhost:8000/*`, so start the API locally
or port-forward it first:

```bash
kubectl port-forward svc/table-maintenance-api 8000:8000 -n lakehouse-control-plane --context retail-lakehouse
```

Then open `http://localhost:5173/console/`.

## Checks

```bash
npm --prefix src/data-platform/frontend run typecheck
npm --prefix src/data-platform/frontend run lint
npm --prefix src/data-platform/frontend test -- --run
npm --prefix src/data-platform/frontend run build
```

## Image

```bash
docker build -t console:dev src/data-platform/frontend
```

The image serves the built files from nginx (`nginx:1.29-alpine`) as a non-root user on port
8080: `/` redirects to `/console/` (a relative redirect), `/console/` serves the app (unknown paths fall back to `index.html` for client-side
routes) and `/console/api/` is proxied to
`table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`. nginx resolves that
name at startup, so the container only starts where it resolves (inside the cluster).
