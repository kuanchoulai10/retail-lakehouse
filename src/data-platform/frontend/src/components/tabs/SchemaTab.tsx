import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import type { CatalogTableApiResponse, SortFieldApiResponse } from "@/api/generated/model";
import { PartitionSpecHistoryPanel } from "@/components/PartitionSpecHistoryPanel";
import { SchemaHistoryPanel } from "@/components/SchemaHistoryPanel";
import { sparkTableDdl } from "@/lib/sparkTableDdl";

function ddlOrProblem(table: CatalogTableApiResponse): { ddl: string } | { problem: string } {
  try {
    return { ddl: sparkTableDdl(table) };
  } catch (error) {
    return { problem: error instanceof Error ? error.message : String(error) };
  }
}

const code = (value: string) => <span className="type-code">{value}</span>;

const sortColumn = createDataTableColumnHelper<SortFieldApiResponse>();

export function SchemaTab({ table }: { table: CatalogTableApiResponse }) {
  const columnName = (sourceId: number) =>
    table.schema.fields.find((field) => field.id === sourceId)?.name ?? String(sourceId);
  const ddl = ddlOrProblem(table);
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
      <SchemaHistoryPanel table={table} />
      <PartitionSpecHistoryPanel table={table} />
      <Panel title="Sort order">
        {table.sort_order.fields.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">Unsorted.</p>
        ) : (
          <DataTable caption="Sort fields" columns={sortColumns} data={table.sort_order.fields} />
        )}
      </Panel>
      <Panel title="DDL (Spark SQL)">
        <p className="type-body-small mb-3 text-on-surface-variant">
          {`Built from the current schema (v${table.schema.schema_id}); earlier versions have no DDL here.`}
        </p>
        {"ddl" in ddl ? (
          <pre
            role="region"
            aria-label="Spark SQL DDL"
            tabIndex={0}
            className="type-code overflow-x-auto rounded-md bg-surface p-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring"
          >
            <code>{ddl.ddl}</code>
          </pre>
        ) : (
          <Banner type="negative" title={`Could not build the DDL: ${ddl.problem}`} />
        )}
      </Panel>
    </div>
  );
}
