# Data Platform Console

Web UI for table owners in front of the table-maintenance API. React + TypeScript, built
with Vite, tested with Vitest and Testing Library. Design:
`docs/superpowers/specs/2026-10-31-data-platform-console-design.md`.

The app is served under `/console/` and calls the API at `/console/api/v1/…`.

## UI

Pages are built from `@retail-lakehouse/design-system` (`src/design-system`): Serendie design
tokens, Radix primitives and Tailwind CSS v4, with three selectable colour themes (KONJO,
ASAGI, KURIKAWA). `src/styles/globals.css` imports the design system's stylesheet; fonts are
Noto Sans and Noto Sans Mono. Decision: `docs/adr/0008-design-system-on-serendie-tokens.md`.

- Build pages from design-system components; a missing one is added to the design system, not
  here. Rules: `CLAUDE.md` and `src/design-system/CLAUDE.md`.
- Use semantic utilities only (`bg-surface`, `text-on-surface-variant`, `border-outline`, …):
  no raw colours, `--sd-*`, `radix-ui` or `lucide-react` in `src/`.
  `src/test/designSystemBoundary.test.ts` fails on any of them.
- The theme is stored in `localStorage` and applied before first paint by the design system.

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
docker build -t console:dev -f src/data-platform/frontend/Dockerfile .
```

The image serves the built files from nginx (`nginx:1.29-alpine`) as a non-root user on port
8080: `/` redirects to `/console/` (a relative redirect), `/console/` serves the app (unknown paths fall back to `index.html` for client-side
routes) and `/console/api/` is proxied to
`table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`. nginx resolves that
name at startup, so the container only starts where it resolves (inside the cluster).
