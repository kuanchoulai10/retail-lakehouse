import { Panel } from "@/components/Panel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function PropertiesPanel({ properties }: { properties: Record<string, string> }) {
  const entries = Object.entries(properties).sort(([a], [b]) => a.localeCompare(b));
  return (
    <Panel title="Properties">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Property</TableHead>
            <TableHead>Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key}>
              <TableCell className="font-mono text-[13px]">{key}</TableCell>
              <TableCell className="break-all font-mono text-[13px]">{value}</TableCell>
            </TableRow>
          ))}
          {entries.length === 0 && (
            <TableRow>
              <TableCell colSpan={2} className="text-center text-muted-foreground">
                No properties.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Panel>
  );
}
