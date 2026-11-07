import type { TableMetadataApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function PropertiesTab({ metadata }: { metadata: TableMetadataApiResponse }) {
  const properties = Object.entries(metadata.properties).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="flex flex-col gap-6">
      <Panel title="Table">
        <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 px-4 py-3 text-sm">
          <dt className="text-muted-foreground">Format version</dt>
          <dd className="font-mono text-[13px]">{metadata.format_version}</dd>
          <dt className="text-muted-foreground">Location</dt>
          <dd className="break-all font-mono text-[13px]">
            <code>{metadata.location}</code>
          </dd>
        </dl>
      </Panel>
      <Panel title="Properties">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Property</TableHead>
              <TableHead>Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {properties.map(([key, value]) => (
              <TableRow key={key}>
                <TableCell className="font-mono text-[13px]">{key}</TableCell>
                <TableCell className="break-all font-mono text-[13px]">{value}</TableCell>
              </TableRow>
            ))}
            {properties.length === 0 && (
              <TableRow>
                <TableCell colSpan={2} className="text-center text-muted-foreground">
                  No properties.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}
