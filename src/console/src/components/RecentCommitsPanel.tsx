import type { TableCommitApiResponse } from "@/api/types";
import { Panel } from "@/components/Panel";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCount, formatTimestamp } from "@/format";

export function RecentCommitsPanel({ commits }: { commits: TableCommitApiResponse[] }) {
  const latest = [...commits]
    .sort((a, b) => b.committed_at.localeCompare(a.committed_at))
    .slice(0, 5);
  return (
    <Panel title="Recent commits">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">Committed</TableHead>
            <TableHead>Operation</TableHead>
            <TableHead className="text-right">Added records</TableHead>
            <TableHead className="px-4 text-right">Added files</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {latest.map((commit) => (
            <TableRow key={commit.snapshot_id}>
              <TableCell className="px-4 tabular-nums">{formatTimestamp(commit.committed_at)}</TableCell>
              <TableCell className="font-mono text-[13px]">{commit.operation ?? "—"}</TableCell>
              <TableCell className="text-right tabular-nums">{formatCount(commit.added_records)}</TableCell>
              <TableCell className="px-4 text-right tabular-nums">
                {formatCount(commit.added_data_files)}
              </TableCell>
            </TableRow>
          ))}
          {latest.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="p-4 text-center text-muted-foreground">
                No commits yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Panel>
  );
}
