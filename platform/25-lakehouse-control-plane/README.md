# Lakehouse Control Plane

Component wave for the future lakehouse control plane. The existing table-maintenance waves (`25-table-maintenance`, `25-tbl-maint-*`) will be consolidated into it later; for now it only creates the namespaces and deploys no components.

## Deployed Resources

```
Namespace: lakehouse-control-plane
Namespace: lakehouse-maintenance-operations
```

## Namespaces

- `lakehouse-control-plane` (created by this wave's `bootstrap.sh`)
- `lakehouse-maintenance-operations` (created by this wave's `bootstrap.sh`)
