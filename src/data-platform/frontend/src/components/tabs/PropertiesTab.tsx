import {
  Badge,
  Banner,
  Button,
  createDataTableColumnHelper,
  DataTable,
  Switch,
} from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useState } from "react";
import type {
  CatalogTableApiResponse,
  CatalogTablePropertiesApiResponse,
  CatalogTablePropertyApiResponse,
} from "@/api/generated/model";
import {
  getGetCatalogTableQueryKey,
  getListCatalogTablePropertiesQueryKey,
  resetCatalogTableProperties,
  useListCatalogTableProperties,
} from "@/api/generated/tables/tables";
import { EditTablePropertiesDialog } from "@/components/forms/EditTablePropertiesDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { ResetAllPropertiesDialog } from "@/components/ResetAllPropertiesDialog";
import { errorMessage } from "@/format";
import { apiNamespace } from "@/lib/catalogPaths";
import { resetDeletesProperty } from "@/lib/resetDeletesProperty";
import { updateErrorMessage } from "@/lib/updateErrorMessage";

const SOURCE_TEXT: Record<NonNullable<CatalogTablePropertyApiResponse["default_source"]>, string> = {
  iceberg: "Iceberg",
  catalog: "Catalog",
  catalog_override: "Forced by catalog",
};

const muted = (text: string) => <span className="type-body-small text-on-surface-variant">{text}</span>;

function canReset(property: CatalogTablePropertyApiResponse): boolean {
  return property.modified && property.resettable;
}

function CurrentValueCell({ property }: { property: CatalogTablePropertyApiResponse }) {
  if (property.current_value !== null) {
    return <span className="type-code block min-w-32 break-all">{property.current_value}</span>;
  }
  // Unset but modified: the default shown is not what the table runs with (the catalog default was
  // never applied, or Iceberg's own value differs from the one it writes on create).
  return (
    <div className="flex min-w-32 flex-col">
      {muted("Not set")}
      {property.modified && muted("Iceberg's own value applies")}
    </div>
  );
}

function DefaultCell({ property }: { property: CatalogTablePropertyApiResponse }) {
  if (property.default_source === null) return muted("No default");
  return (
    <div className="flex min-w-32 flex-col">
      {property.default_value === null ? (
        muted("Not set")
      ) : (
        <span className="type-code break-all">{property.default_value}</span>
      )}
      {property.default_source !== null && muted(SOURCE_TEXT[property.default_source])}
    </div>
  );
}

// The row buttons reach the reset through context, so the columns stay one module-level definition
// (a new definition each render would remount every cell, and a clicked button would lose focus).
const ResetContext = createContext<{ pending: boolean; onReset: (key: string) => void }>({
  pending: false,
  onReset: () => undefined,
});

function RowAction({ property }: { property: CatalogTablePropertyApiResponse }) {
  const { pending, onReset } = useContext(ResetContext);
  if (!property.modified) return null;
  if (!property.resettable) return muted("Not resettable");
  const verb = resetDeletesProperty(property) ? "Delete" : "Reset";
  return (
    <Button
      type="button"
      styleType="outlined"
      size="small"
      aria-label={`${verb} ${property.key}`}
      disabled={pending}
      onClick={() => onReset(property.key)}
    >
      {verb}
    </Button>
  );
}

const column = createDataTableColumnHelper<CatalogTablePropertyApiResponse>();

const columns = column.columns([
  column.accessor("key", {
    header: "Property",
    enableSorting: false,
    cell: (info) => {
      const property = info.row.original;
      return (
        <div className="flex min-w-48 flex-col">
          <span className="type-code break-all">{property.key}</span>
          {property.description !== null && muted(property.description)}
        </div>
      );
    },
  }),
  column.accessor("current_value", {
    header: "Current value",
    enableSorting: false,
    cell: (info) => <CurrentValueCell property={info.row.original} />,
  }),
  column.display({
    id: "default",
    header: "Default",
    cell: (info) => <DefaultCell property={info.row.original} />,
  }),
  column.display({
    id: "state",
    header: () => <span className="sr-only">Changed</span>,
    cell: (info) => {
      const property = info.row.original;
      if (property.custom) return <Badge>Custom</Badge>;
      return property.modified ? <Badge>Modified</Badge> : null;
    },
  }),
  column.display({
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: (info) => (
      <div className="flex justify-end">
        <RowAction property={info.row.original} />
      </div>
    ),
  }),
]);

interface PropertiesViewProps {
  table: CatalogTableApiResponse;
  properties: CatalogTablePropertiesApiResponse;
}

// Every property the table could hold, next to its default, with reset per row or for all of
// them. After every write, failed or not, the table and its properties are refetched.
function PropertiesView({ table, properties }: PropertiesViewProps) {
  const queryClient = useQueryClient();
  const ns = apiNamespace(table.namespace);
  const [modifiedOnly, setModifiedOnly] = useState(false);
  const [dialog, setDialog] = useState<"edit" | "reset-all" | null>(null);

  const reset = useMutation({
    mutationFn: (keys: string[]) =>
      resetCatalogTableProperties(table.catalog, ns, table.name, { expected_uuid: properties.uuid, keys }),
    onSettled: async (_data, error) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getListCatalogTablePropertiesQueryKey(table.catalog, ns, table.name) }),
        queryClient.invalidateQueries({ queryKey: getGetCatalogTableQueryKey(table.catalog, ns, table.name) }),
      ]);
      if (error === null) setDialog(null);
    },
  });

  const resettable = properties.properties.filter(canReset);
  const rows = modifiedOnly ? properties.properties.filter((p) => p.modified) : properties.properties;
  const error = reset.isError ? updateErrorMessage(reset.error, "table") : null;

  function resetOne(key: string) {
    reset.mutate([key]);
  }

  function openResetAll() {
    reset.reset();
    setDialog("reset-all");
  }

  // A failure the dialog showed goes with it, so it is not shown again on the page.
  function closeResetAll() {
    reset.reset();
    setDialog(null);
  }

  return (
    <section aria-label="Properties" className="flex min-w-0 flex-col gap-3">
      <header className="flex flex-wrap items-center gap-2">
        <Switch label="Show modified only" checked={modifiedOnly} onCheckedChange={setModifiedOnly} />
        <div className="ml-auto flex flex-wrap gap-2">
          <Button
            type="button"
            styleType="outlined"
            size="small"
            disabled={resettable.length === 0 || reset.isPending}
            onClick={openResetAll}
          >
            Reset all to default
          </Button>
          <Button type="button" size="small" onClick={() => setDialog("edit")}>
            Edit properties
          </Button>
        </div>
      </header>
      <p className="type-body-small text-on-surface-variant">
        Defaults of Iceberg {properties.iceberg_version}, unless the catalog sets its own.
      </p>
      {error !== null && dialog === null && <Banner type="negative" title={error} />}
      <ResetContext value={{ pending: reset.isPending, onReset: resetOne }}>
        <DataTable
          caption="Property values and defaults"
          columns={columns}
          data={rows}
          getRowId={(row) => row.key}
          emptyState={modifiedOnly ? "No modified properties." : "No properties."}
        />
      </ResetContext>
      {dialog === "edit" && <EditTablePropertiesDialog table={table} onClose={() => setDialog(null)} />}
      {dialog === "reset-all" && (
        <ResetAllPropertiesDialog
          fullPath={[table.catalog, ...table.namespace, table.name].join(" / ")}
          properties={resettable}
          isPending={reset.isPending}
          error={error}
          onConfirm={() => reset.mutate(resettable.map((p) => p.key))}
          onClose={closeResetAll}
        />
      )}
    </section>
  );
}

export function PropertiesTab({ table }: { table: CatalogTableApiResponse }) {
  const properties = useListCatalogTableProperties(table.catalog, apiNamespace(table.namespace), table.name);
  if (properties.isPending) return <PanelSkeleton label="Loading properties…" />;
  if (properties.isError) {
    return <Banner type="negative" title={`Could not load properties: ${errorMessage(properties.error)}`} />;
  }
  return <PropertiesView table={table} properties={properties.data} />;
}
