import type { JsonObject, TableMetadataApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function fieldsOf(spec: JsonObject | undefined): JsonObject[] {
  return Array.isArray(spec?.fields) ? (spec.fields as JsonObject[]) : [];
}

export function SchemaPanel({ metadata }: { metadata: TableMetadataApiResponse }) {
  const partitionFields = fieldsOf(metadata.specs.at(-1));
  return (
    <Panel title="Schema">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">Column</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Required</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metadata.schema_fields.map((field) => (
            <TableRow key={String(field.field_id)}>
              <TableCell className="px-4 font-mono text-[13px]">{String(field.name)}</TableCell>
              <TableCell className="font-mono text-[13px]">{String(field.type)}</TableCell>
              <TableCell>{field.required ? "yes" : "no"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <h3 className="border-y border-border bg-card px-4 py-2 text-sm font-medium">Partition spec</h3>
      {partitionFields.length === 0 ? (
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
            {partitionFields.map((field) => (
              <TableRow key={String(field.field_id)}>
                <TableCell className="px-4 font-mono text-[13px]">{String(field.name)}</TableCell>
                <TableCell className="font-mono text-[13px]">{String(field.source_column)}</TableCell>
                <TableCell className="font-mono text-[13px]">{String(field.transform)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Panel>
  );
}
