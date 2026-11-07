import type { CatalogTableApiResponse } from "@/api/catalogTypes";
import { Panel } from "@/components/Panel";
import { SchemaFieldsPanel } from "@/components/SchemaFieldsPanel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { sparkTableDdl } from "@/lib/sparkTableDdl";

function ddlOrProblem(table: CatalogTableApiResponse): { ddl: string } | { problem: string } {
  try {
    return { ddl: sparkTableDdl(table) };
  } catch (error) {
    return { problem: error instanceof Error ? error.message : String(error) };
  }
}

export function SchemaTab({ table }: { table: CatalogTableApiResponse }) {
  const columnName = (sourceId: number) =>
    table.schema.fields.find((field) => field.id === sourceId)?.name ?? String(sourceId);
  const ddl = ddlOrProblem(table);
  const mono = "font-mono text-[13px]";
  return (
    <div className="flex flex-col gap-6">
      <SchemaFieldsPanel schema={table.schema} />
      <Panel title="Partition spec">
        {table.partition_spec.fields.length === 0 ? (
          <p className="p-4 text-[13px] text-muted-foreground">Unpartitioned.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-4">Field</TableHead>
                <TableHead>Source column</TableHead>
                <TableHead>Transform</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {table.partition_spec.fields.map((field) => (
                <TableRow key={field.field_id}>
                  <TableCell className={`px-4 ${mono}`}>{field.name}</TableCell>
                  <TableCell className={mono}>{columnName(field.source_id)}</TableCell>
                  <TableCell className={mono}>{field.transform}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
      <Panel title="Sort order">
        {table.sort_order.fields.length === 0 ? (
          <p className="p-4 text-[13px] text-muted-foreground">Unsorted.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-4">Source column</TableHead>
                <TableHead>Transform</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Null order</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {table.sort_order.fields.map((field, index) => (
                <TableRow key={index}>
                  <TableCell className={`px-4 ${mono}`}>{columnName(field.source_id)}</TableCell>
                  <TableCell className={mono}>{field.transform}</TableCell>
                  <TableCell className={mono}>{field.direction}</TableCell>
                  <TableCell className={mono}>{field.null_order}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
      <Panel title="DDL (Spark SQL)">
        {"ddl" in ddl ? (
          <pre className="overflow-x-auto p-4 font-mono text-[13px]">
            <code>{ddl.ddl}</code>
          </pre>
        ) : (
          <p role="alert" className="p-4 text-sm text-destructive">
            Could not build the DDL: {ddl.problem}
          </p>
        )}
      </Panel>
    </div>
  );
}
