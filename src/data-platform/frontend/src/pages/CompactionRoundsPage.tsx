import { Banner, createDataTableColumnHelper, DataTable, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { Link, useSearchParams } from "react-router";
import { useListCompactionRounds } from "@/api/generated/compaction-rounds/compaction-rounds";
import type {
  CompactionRoundApiResponse,
  CompactionRoundPickApiResponse,
  CompactionRoundSkipApiResponse,
} from "@/api/generated/model";
import { PageHeader } from "@/components/PageHeader";
import { PriorityText } from "@/components/PriorityText";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatCount, formatTimestamp } from "@/format";
import { priorityWeightsText } from "@/lib/priorityText";
import { candidatesPathOf, skipReasonText, usedText } from "@/lib/roundText";
import { useSchedulerPriorities } from "@/lib/useSchedulerPriorities";

const ROUNDS_SHOWN = 50;
const REFRESH_MS = 30_000;
const SKELETON_ROWS = 5;
const NO_ROUNDS: CompactionRoundApiResponse[] = [];

type Entry = CompactionRoundPickApiResponse | CompactionRoundSkipApiResponse;

function twoDecimals(value: number): string {
  return value.toFixed(2);
}

function gbHours(value: number): string {
  return value > 0 && value < 0.005 ? "< 0.01" : twoDecimals(value);
}

function entryKey(entry: Entry): string {
  return JSON.stringify([entry.table_uuid, entry.partition.spec_id, entry.partition.values]);
}

// A round is named by when it started, as the Started column shows it; its workflow id is
// secondary detail.
function roundName(round: CompactionRoundApiResponse): string {
  return formatTimestamp(round.started_at);
}

function TableCell({ entry }: { entry: Entry }) {
  const path = candidatesPathOf(entry.table);
  if (entry.table_name === null || path === null) {
    return (
      <span className="flex flex-col">
        <span>Dropped table</span>{" "}
        <span className="font-mono type-body-small text-on-surface-variant">{entry.table_uuid}</span>
      </span>
    );
  }
  return (
    <TextLink asChild className="font-mono">
      <Link to={path}>{entry.table_name}</Link>
    </TextLink>
  );
}

// The columns a pick and a skip share; a skip adds its reason.
function entryColumns<T extends Entry>() {
  const column = createDataTableColumnHelper<T>();
  return column.columns([
    column.accessor((e) => e.table_name ?? e.table_uuid, {
      id: "table",
      header: "Table",
      enableSorting: false,
      cell: (info) => <TableCell entry={info.row.original} />,
    }),
    column.accessor((e) => e.partition_label, {
      id: "partition",
      header: "Partition",
      enableSorting: false,
      cell: (info) => <span className="font-mono">{info.getValue()}</span>,
    }),
    column.accessor((e) => e.priority, {
      id: "priority",
      header: "Priority",
      enableSorting: false,
      cell: (info) => <PriorityText priority={info.getValue()} />,
    }),
    column.accessor((e) => e.score, {
      id: "score",
      header: "Score",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{twoDecimals(info.getValue())}</span>,
    }),
    column.accessor((e) => e.weighted_score, {
      id: "weighted_score",
      header: "Weighted",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{twoDecimals(info.getValue())}</span>,
    }),
    column.accessor((e) => e.estimated_gb_hours, {
      id: "gb_hours",
      header: "Est. GB·h",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{gbHours(info.getValue())}</span>,
    }),
    column.accessor((e) => e.overdue, {
      id: "overdue",
      header: "Overdue",
      enableSorting: false,
      cell: (info) => (info.getValue() ? <StatusBadge status="overdue" /> : "—"),
    }),
  ]);
}

const pickColumns = entryColumns<CompactionRoundPickApiResponse>();

const skipColumn = createDataTableColumnHelper<CompactionRoundSkipApiResponse>();
const skipColumns = skipColumn.columns([
  ...entryColumns<CompactionRoundSkipApiResponse>(),
  skipColumn.accessor((s) => skipReasonText(s.reason), { id: "reason", header: "Reason", enableSorting: false }),
]);

// A busy table's partitions are only counted, not kept as skips, so they never hide the budget's.
function busyText(count: number): string {
  const partitions = count === 1 ? "partition" : "partitions";
  return `Left for a later round without ranking: ${formatCount(count)} ${partitions} of tables still busy with compaction.`;
}

const SKIP_REASONS_TEXT =
  "Budget used: the round's GB·h budget ran out. Table's share used: the table already has as many partitions as " +
  "one round gives a table. Table busy: the table is still compacting what an earlier round granted.";

function WeightedNote() {
  const priorities = useSchedulerPriorities();
  const weights = priorities === undefined ? "" : ` (${priorityWeightsText(priorities)})`;
  return (
    <p className="type-body-small text-on-surface-variant">
      {`Weighted is the score times its priority's weight${weights}. Overdue: it waited longer than its priority allows.`}
    </p>
  );
}

function RoundDetail({ round }: { round: CompactionRoundApiResponse }) {
  const shown = round.skips.length;
  const name = roundName(round);
  return (
    <div className="flex flex-col gap-4 py-2">
      <WeightedNote />
      <DataTable
        caption={`Partitions round ${name} granted`}
        columns={pickColumns}
        data={round.picks}
        getRowId={entryKey}
        emptyState="Nothing was pending, so nothing was granted."
      />
      {round.skipped_total > 0 && (
        <>
          <p className="type-body-small text-on-surface-variant">
            {shown < round.skipped_total
              ? `The first ${formatCount(shown)} of ${formatCount(round.skipped_total)} skipped partitions, in rank order.`
              : "The skipped partitions, in rank order."}
          </p>
          <DataTable
            caption={`Partitions round ${name} skipped`}
            columns={skipColumns}
            data={round.skips}
            getRowId={entryKey}
          />
          <p className="type-body-small text-on-surface-variant">{SKIP_REASONS_TEXT}</p>
        </>
      )}
      {round.busy_skipped > 0 && (
        <p className="type-body-small text-on-surface-variant">{busyText(round.busy_skipped)}</p>
      )}
      <p className="type-body-small text-on-surface-variant">
        Workflow id <span className="font-mono">{round.round_id}</span>
      </p>
    </div>
  );
}

const column = createDataTableColumnHelper<CompactionRoundApiResponse>();
const roundColumns = column.columns([
  column.accessor("started_at", {
    header: "Started",
    enableSorting: false,
    cell: (info) => (
      <time dateTime={info.getValue()} className="tabular-nums whitespace-nowrap">
        {formatTimestamp(info.getValue())}
      </time>
    ),
  }),
  column.accessor("budget_gb_hours", {
    header: "Budget GB·h",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{twoDecimals(info.getValue())}</span>,
  }),
  column.accessor((r) => usedText(r), {
    id: "used",
    header: "Used GB·h",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums whitespace-nowrap">{info.getValue()}</span>,
  }),
  column.accessor((r) => r.picks.length, {
    id: "picked",
    header: "Picked",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{formatCount(info.getValue())}</span>,
  }),
  column.accessor("skipped_total", {
    header: "Skipped",
    enableSorting: false,
    cell: (info) => <span className="tabular-nums">{formatCount(info.getValue())}</span>,
  }),
]);

function LoadingRows() {
  return (
    <div className="grid gap-3 py-1">
      {Array.from({ length: SKELETON_ROWS }, (_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

// The rounds of the compaction scheduler, newest first: each grants the best pending partitions of
// every table (score times the priority's weight) while its GB·hour budget lasts, and a row opens
// to what it granted and the first candidates it left, with why.
export function CompactionRoundsPage() {
  const rounds = useListCompactionRounds({ limit: ROUNDS_SHOWN }, { query: { refetchInterval: REFRESH_MS } });
  // A link from a granted candidate names its round, which starts open.
  const [searchParams] = useSearchParams();
  const linked = searchParams.get("round");

  return (
    <section>
      <PageHeader title="Compaction rounds">
        <span>
          Each round grants the best pending partitions of every table, by score times priority weight, while its
          budget lasts. The newest {ROUNDS_SHOWN} are shown.
        </span>
      </PageHeader>
      {rounds.isError && (
        <Banner type="negative" title={`Could not load compaction rounds: ${errorMessage(rounds.error)}`} />
      )}
      {!rounds.isError && (
        <div aria-busy={rounds.isPending}>
          <DataTable
            caption="Compaction rounds, newest first"
            columns={roundColumns}
            data={rounds.data ?? NO_ROUNDS}
            getRowId={(round) => round.round_id}
            getRowLabel={(round) => `round ${roundName(round)}`}
            initialExpandedRowIds={linked === null ? undefined : [linked]}
            renderDetail={(round) => <RoundDetail round={round} />}
            emptyState={rounds.isPending ? <LoadingRows /> : "No compaction round has run yet."}
          />
        </div>
      )}
    </section>
  );
}
