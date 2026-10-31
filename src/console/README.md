# Data Platform Console

Web UI for table owners in front of the table-maintenance API. React + TypeScript, built
with Vite, tested with Vitest and Testing Library. Design:
`docs/superpowers/specs/2026-10-31-data-platform-console-design.md`.

The app is served under `/console/` and calls the API at `/console/api/v1/…`.

## Develop

```bash
npm --prefix src/console install
npm --prefix src/console run dev
```

The dev server proxies `/console/api/*` to `http://localhost:8000/*`, so start the API locally
or port-forward it first:

```bash
kubectl port-forward svc/table-maintenance-api 8000:8000 -n lakehouse-control-plane --context retail-lakehouse
```

Then open `http://localhost:5173/console/`.

## Checks

```bash
npm --prefix src/console run typecheck
npm --prefix src/console run lint
npm --prefix src/console test -- --run
npm --prefix src/console run build
```

## Image

```bash
docker build -t console:dev src/console
```

The image serves the built files from nginx (`nginx:1.29-alpine`) as a non-root user on port
8080: `/console/` serves the app (unknown paths fall back to `index.html` for client-side
routes) and `/console/api/` is proxied to
`table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`. nginx resolves that
name at startup, so the container only starts where it resolves (inside the cluster).
