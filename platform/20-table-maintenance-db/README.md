# Table Maintenance PostgreSQL

Deploys PostgreSQL 17.11 as the store of the table maintenance control plane into the `lakehouse-control-plane` namespace, which this wave creates with the ambient label. The control plane's Helm chart (`25-lakehouse-control-plane`) only connects to it: its `migrate` Job creates the schema, and its `database` values name the host, the database, the user and the Secret that holds the password.

The database used to be part of the chart. It is a wave of its own so that deleting or reinstalling the release never deletes the data. In open-source charts the database is a dependency the operator brings, not something the application release owns.

## Deployed Resources

```
Namespace: lakehouse-control-plane
├── table-maintenance-db                  (Deployment, strategy Recreate)
├── table-maintenance-db                  (Service, port 5432)
├── table-maintenance-db                  (PersistentVolumeClaim, 5Gi)
└── table-maintenance-db                  (Secret: password)
```

## Connection Info

| Setting | Value |
|---------|-------|
| Host | `table-maintenance-db.lakehouse-control-plane.svc.cluster.local:5432` |
| Database | `table_maintenance` |
| User | `table_maintenance` |
| Password | Secret `table-maintenance-db`, key `password` |

`bootstrap.sh` creates the Secret with a random 48-character hex password when it does not exist yet, and never changes an existing one. The password is in no file in the repository. The chart reads it through `database.existingSecret` and refuses to render without one.

## Sync Wave

Wave 20. The control plane (wave 25) depends on it, and `tasks/apps.yml` validates this wave before it bootstraps wave 25.

## Data

The data lives on the PersistentVolumeClaim. Deleting this wave's objects, or the namespace, loses it. A cluster that still runs the chart's own `table-maintenance-db` (a release before KCL-112) is rebuilt (`task offboard` + `task onboard`) rather than upgraded: a `helm upgrade` would delete the objects this wave applies under the same names.

## Installation

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/20-table-maintenance-db/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/20-table-maintenance-db/validate.sh
```
