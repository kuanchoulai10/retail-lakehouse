import { createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import type { SchemaApiResponse, SchemaFieldApiResponse } from "@/api/generated/model";

const column = createDataTableColumnHelper<SchemaFieldApiResponse>();

const columns = column.columns([
  column.accessor("id", {
    header: "Id",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
  }),
  column.accessor("name", {
    header: "Column",
    enableSorting: false,
    cell: (info) => <span className="type-code">{info.getValue()}</span>,
  }),
  column.accessor("type", {
    header: "Type",
    enableSorting: false,
    cell: (info) => <span className="type-code block min-w-48 break-all">{info.getValue()}</span>,
  }),
  column.accessor("required", {
    header: "Required",
    enableSorting: false,
    cell: (info) => (info.getValue() ? "yes" : "no"),
  }),
  column.accessor("doc", {
    header: "Doc",
    enableSorting: false,
    cell: (info) => <span className="block min-w-48 text-on-surface-variant">{info.getValue() ?? "—"}</span>,
  }),
]);

export function SchemaFieldsPanel({ schema }: { schema: SchemaApiResponse }) {
  return (
    <Panel
      title="Schema"
      actions={<span className="type-body-small text-on-surface-variant">Schema id {schema.schema_id}</span>}
    >
      <DataTable
        caption="Schema columns"
        columns={columns}
        data={schema.fields}
        getRowId={(field) => String(field.id)}
        emptyState="No columns."
      />
    </Panel>
  );
}
