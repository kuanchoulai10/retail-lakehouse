import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import type { CatalogTableApiResponse, PartitionFieldApiResponse, SortFieldApiResponse } from "@/api/generated/model";
import { SchemaFieldsPanel } from "@/components/SchemaFieldsPanel";
import { sparkTableDdl } from "@/lib/sparkTableDdl";

function ddlOrProblem(table: CatalogTableApiResponse): { ddl: string } | { problem: string } {
  try {
    return { ddl: sparkTableDdl(table) };
  } catch (error) {
    return { problem: error instanceof Error ? error.message : String(error) };
  }
}

const code = (value: string) => <span className="type-code">{value}</span>;

const partitionColumn = createDataTableColumnHelper<PartitionFieldApiResponse>();
const sortColumn = createDataTableColumnHelper<SortFieldApiResponse>();

export function SchemaTab({ table }: { table: CatalogTableApiResponse }) {
  const columnName = (sourceId: number) =>
    table.schema.fields.find((field) => field.id === sourceId)?.name ?? String(sourceId);
  const ddl = ddlOrProblem(table);
  const partitionColumns = partitionColumn.columns([
    partitionColumn.accessor("name", { header: "Field", enableSorting: false, cell: (info) => code(info.getValue()) }),
    partitionColumn.accessor((field) => columnName(field.source_id), {
      id: "source",
      header: "Source column",
      enableSorting: false,
      cell: (info) => code(info.getValue()),
    }),
    partitionColumn.accessor("transform", {
      header: "Transform",
      enableSorting: false,
      cell: (info) => code(info.getValue()),
    }),
  ]);
  const sortColumns = sortColumn.columns([
    sortColumn.accessor((field) => columnName(field.source_id), {
      id: "source",
      header: "Source column",
      enableSorting: false,
      cell: (info) => code(info.getValue()),
    }),
    sortColumn.accessor("transform", { header: "Transform", enableSorting: false, cell: (info) => code(info.getValue()) }),
    sortColumn.accessor("direction", { header: "Direction", enableSorting: false, cell: (info) => code(info.getValue()) }),
    sortColumn.accessor("null_order", { header: "Null order", enableSorting: false, cell: (info) => code(info.getValue()) }),
  ]);
  return (
    <div className="flex flex-col gap-6">
      <SchemaFieldsPanel schema={table.schema} />
      <Panel title="Partition spec">
        {table.partition_spec.fields.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">Unpartitioned.</p>
        ) : (
          <DataTable
            caption="Partition fields"
            columns={partitionColumns}
            data={table.partition_spec.fields}
            getRowId={(field) => String(field.field_id)}
          />
        )}
      </Panel>
      <Panel title="Sort order">
        {table.sort_order.fields.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">Unsorted.</p>
        ) : (
          <DataTable caption="Sort fields" columns={sortColumns} data={table.sort_order.fields} />
        )}
      </Panel>
      <Panel title="DDL (Spark SQL)">
        {"ddl" in ddl ? (
          <pre className="type-code overflow-x-auto rounded-md bg-surface p-3">
            <code>{ddl.ddl}</code>
          </pre>
        ) : (
          <Banner type="negative" title={`Could not build the DDL: ${ddl.problem}`} />
        )}
      </Panel>
    </div>
  );
}
