import type { SchemaApiResponse } from "@/api/catalogTypes";
import { Panel } from "@/components/Panel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function SchemaFieldsPanel({ schema }: { schema: SchemaApiResponse }) {
  return (
    <Panel title="Schema" actions={<span className="text-[13px] text-muted-foreground">Schema id {schema.schema_id}</span>}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">Id</TableHead>
            <TableHead>Column</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Required</TableHead>
            <TableHead>Doc</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {schema.fields.map((field) => (
            <TableRow key={field.id}>
              <TableCell className="px-4 tabular-nums">{field.id}</TableCell>
              <TableCell className="font-mono text-[13px]">{field.name}</TableCell>
              <TableCell className="font-mono text-[13px] whitespace-normal break-all">{field.type}</TableCell>
              <TableCell>{field.required ? "yes" : "no"}</TableCell>
              <TableCell className="whitespace-normal text-muted-foreground">{field.doc ?? "—"}</TableCell>
            </TableRow>
          ))}
          {schema.fields.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                No columns.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Panel>
  );
}
