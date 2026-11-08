import { createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";

interface PropertyRow {
  key: string;
  value: string;
}

const column = createDataTableColumnHelper<PropertyRow>();

const columns = column.columns([
  column.accessor("key", {
    header: "Property",
    enableSorting: false,
    cell: (info) => <span className="type-code">{info.getValue()}</span>,
  }),
  column.accessor("value", {
    header: "Value",
    enableSorting: false,
    cell: (info) => <span className="type-code block min-w-48 break-all">{info.getValue()}</span>,
  }),
]);

export function PropertiesPanel({ properties }: { properties: Record<string, string> }) {
  const rows = Object.entries(properties)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => ({ key, value }));
  return (
    <Panel title="Properties">
      <DataTable
        caption="Property values"
        columns={columns}
        data={rows}
        getRowId={(row) => row.key}
        emptyState="No properties."
      />
    </Panel>
  );
}
