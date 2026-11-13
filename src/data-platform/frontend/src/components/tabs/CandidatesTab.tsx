import { Banner, createDataTableColumnHelper, DataTable, Panel, TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";
import { useListCompactionCandidates } from "@/api/generated/compaction-candidates/compaction-candidates";
import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { OverdueNote } from "@/components/OverdueNote";
import { PriorityText } from "@/components/PriorityText";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatBytes, formatCount, formatGbHours, formatTimestamp } from "@/format";
import { roundPath, whyNotPicked } from "@/lib/candidateText";

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
    column.accessor("priority", {
      header: "Priority",
      enableSorting: false,
      cell: (info) => <PriorityText priority={info.getValue()} />,
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
      cell: (info) => <span className="tabular-nums">{formatGbHours(info.getValue())}</span>,
    }),
    column.accessor("state", {
      header: "State",
      enableSorting: false,
      cell: (info) => (
        <span className="flex flex-wrap items-center gap-1">
          <StatusBadge status={info.getValue()} />
          {info.row.original.overdue && <OverdueNote candidate={info.row.original} />}
        </span>
      ),
    }),
    column.accessor((candidate) => whyNotPicked(candidate, partitionsPerRun), {
      id: "why",
      header: "Why not picked",
      enableSorting: false,
      cell: (info) => <WhyNotPicked candidate={info.row.original} text={info.getValue()} />,
    }),
  ]);
}

// A granted candidate's round is named by its start time and links to the rounds page with that
// round open.
function WhyNotPicked({ candidate, text }: { candidate: CompactionCandidateApiResponse; text: string }) {
  const roundId = candidate.granted_round_id;
  const started = candidate.granted_round_started_at;
  if (candidate.state !== "granted" || roundId === null || started === null) return text;
  return (
    <>
      Granted in round{" "}
      <TextLink asChild inline>
        <Link to={roundPath(roundId)}>{formatTimestamp(started)}</Link>
      </TextLink>
    </>
  );
}

function partitionKey(candidate: CompactionCandidateApiResponse): string {
  return JSON.stringify([candidate.partition.spec_id, candidate.partition.values]);
}

// The partitions of a table that need compaction, best first, with what each is worth and why it
// is not in a run yet: held by a filter or because compaction is not due, waiting for a round,
// granted by one, or already in a run.
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
        Each compaction round grants the best pending partitions across all tables while its budget lasts, at most{" "}
        {n} per table.{" "}
        <TextLink asChild inline>
          <Link to="/compaction-rounds">See the compaction rounds</Link>
        </TextLink>
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
