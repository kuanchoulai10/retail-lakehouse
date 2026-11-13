import { Banner, createDataTableColumnHelper, DataTable, Panel } from "@retail-lakehouse/design-system";
import { useListCompactionCandidates } from "@/api/generated/compaction-candidates/compaction-candidates";
import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatBytes, formatCount } from "@/format";
import { whyNotPicked } from "@/lib/candidateText";

function twoDecimals(value: number): string {
  return value.toFixed(2);
}

function candidateColumns(partitionsPerRun: number) {
  const column = createDataTableColumnHelper<CompactionCandidateApiResponse>();
  return column.columns([
    column.accessor("partition_label", {
      header: "Partition",
      enableSorting: false,
      cell: (info) => <span className="font-mono">{info.getValue()}</span>,
    }),
    column.accessor("score", {
      header: "Score",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{twoDecimals(info.getValue())}</span>,
    }),
    column.accessor("reducible_files", {
      header: "Removable files",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{formatCount(info.getValue())}</span>,
    }),
    column.accessor("data_bytes", {
      header: "Data",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums whitespace-nowrap">{formatBytes(info.getValue())}</span>,
    }),
    column.accessor("estimated_gb_hours", {
      header: "Est. GB·h",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{twoDecimals(info.getValue())}</span>,
    }),
    column.accessor("state", {
      header: "State",
      enableSorting: false,
      cell: (info) => <StatusBadge status={info.getValue()} />,
    }),
    column.accessor((candidate) => whyNotPicked(candidate, partitionsPerRun), {
      id: "why",
      header: "Why not picked",
      enableSorting: false,
    }),
  ]);
}

function partitionKey(candidate: CompactionCandidateApiResponse): string {
  return JSON.stringify([candidate.partition.spec_id, candidate.partition.values]);
}

// The partitions of a table that need compaction, best first, with what each is worth and why it
// is not in the next run: held by a filter, below the top N, or already in a run.
export function CandidatesTab({ tableUuid }: { tableUuid: string }) {
  const candidates = useListCompactionCandidates(tableUuid);

  if (candidates.isPending) return <PanelSkeleton label="Loading compaction candidates…" />;
  if (candidates.isError) {
    return (
      <Banner type="negative" title={`Could not load compaction candidates: ${errorMessage(candidates.error)}`} />
    );
  }
  const n = candidates.data.partitions_per_run;
  return (
    <Panel title="Compaction candidates">
      <p className="type-body-small text-on-surface-variant mb-3">
        {`Each scheduled run compacts the top ${n} pending ${n === 1 ? "partition" : "partitions"}.`}
      </p>
      <DataTable
        caption="Compaction candidates, best first"
        columns={candidateColumns(n)}
        data={candidates.data.candidates}
        getRowId={partitionKey}
        emptyState="No partition needs compaction."
      />
    </Panel>
  );
}
