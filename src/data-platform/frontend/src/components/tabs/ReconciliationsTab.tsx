import {
  Badge,
  Banner,
  Button,
  Drawer,
  IconChevronDown,
  IconChevronRight,
  Timeline,
  TimelineItem,
} from "@retail-lakehouse/design-system";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import type { TableReconciliationApiResponse } from "@/api/generated/model";
import {
  getListTableReconciliationsQueryKey,
  listTableReconciliations,
  useGetTableReconciliation,
} from "@/api/generated/table-reconciliations/table-reconciliations";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { ReconciliationPanel } from "@/components/tabs/ReconciliationPanel";
import {
  foldKey,
  foldText,
  formatTime,
  headline,
  isManualRun,
  mainWakeText,
  policyLabel,
} from "@/components/tabs/reconciliationText";
import { RunLink } from "@/components/tabs/RunLink";
import { useOpenRecord } from "@/components/tabs/useOpenRecord";
import { errorMessage, formatRelativeTime, formatTimestamp } from "@/format";
import { isGone } from "@/lib/isGone";

const PAGE_SIZE = 50;

const REFRESH_FAILED = "Could not refresh. Showing what was last read.";

const DAY_FORMAT = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

// A line of the timeline: one reconciliation, or a stretch of alike ones folded into one line.
type Line = { kind: "record"; record: TableReconciliationApiResponse } | { kind: "fold"; key: string; records: TableReconciliationApiResponse[] };

type Day = { date: string; records: TableReconciliationApiResponse[] };

// Records come newest first, so the days come out newest first too.
function groupedByDay(records: TableReconciliationApiResponse[]): Day[] {
  const days: Day[] = [];
  for (const record of records) {
    const date = DAY_FORMAT.format(new Date(record.reconciled_at));
    const last = days.at(-1);
    if (last?.date === date) last.records.push(record);
    else days.push({ date, records: [record] });
  }
  return days;
}

// Consecutive reconciliations that started nothing and read the same fold into one line, so
// hourly quiet passes or the skips of a paused table do not drown the ones that did something
// (spec anti-goal). A different headline, or one that started something, breaks the fold.
function folded(records: TableReconciliationApiResponse[]): Line[] {
  const lines: Line[] = [];
  for (const record of records) {
    const key = foldKey(record);
    const last = lines.at(-1);
    if (key !== null && last?.kind === "fold" && last.key === key) last.records.push(record);
    else lines.push(key === null ? { kind: "record", record } : { kind: "fold", key, records: [record] });
  }
  return lines.map((line) => (line.kind === "fold" && line.records.length === 1 ? { kind: "record", record: line.records[0]! } : line));
}

// The run the line links to: only when exactly one operation started a run, since a timeline line holds
// one action; the details list one link per operation.
function onlyStartedRun(r: TableReconciliationApiResponse): string | null {
  const runIds = r.operations.flatMap((op) => (op.result === "started" && op.run_id !== null ? [op.run_id] : []));
  return runIds.length === 1 ? runIds[0]! : null;
}

// Filled when the reconciliation started, or in dry run would have started, something.
function startedSomething(r: TableReconciliationApiResponse): boolean {
  return r.operations.some((op) => op.result === "started" || op.result === "would_start");
}

function RecordLine({ record, onOpen }: { record: TableReconciliationApiResponse; onOpen: () => void }) {
  const runId = onlyStartedRun(record);
  return (
    <TimelineItem
      marker={startedSomething(record) ? "filled" : "outlined"}
      title={
        <span className="flex flex-wrap items-center gap-2">
          {headline(record)}
          {record.dry_run && !isManualRun(record) && <Badge>Dry run</Badge>}
        </span>
      }
      description={
        <>
          {mainWakeText(record)} at <span className="tabular-nums">{formatTime(record.reconciled_at)}</span>,{" "}
          <time dateTime={record.reconciled_at} title={formatTimestamp(record.reconciled_at)}>
            {formatRelativeTime(record.reconciled_at)}
          </time>
          {" · "}
          <span className="font-mono">{policyLabel(record)}</span>
        </>
      }
      onSelect={onOpen}
      trailingAction={runId === null ? undefined : <RunLink runId={runId} label="Run" className="whitespace-nowrap" />}
    />
  );
}

function FoldLine({ records, onOpen }: { records: TableReconciliationApiResponse[]; onOpen: (r: TableReconciliationApiResponse) => void }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  return (
    <TimelineItem
      marker="dashed"
      title={
        <span className="flex items-center gap-1 tabular-nums">
          {open ? <IconChevronDown aria-hidden="true" size={16} /> : <IconChevronRight aria-hidden="true" size={16} />}
          {foldText(records)}
        </span>
      }
      aria-expanded={open}
      aria-controls={open ? listId : undefined}
      onSelect={() => setOpen((value) => !value)}
    >
      {open && (
        <Timeline id={listId} nested>
          {records.map((record) => (
            <TimelineItem
              key={record.reconciliation_id}
              title={
                <span className="tabular-nums">
                  {mainWakeText(record)} at {formatTime(record.reconciled_at)}
                </span>
              }
              onSelect={() => onOpen(record)}
            />
          ))}
        </Timeline>
      )}
    </TimelineItem>
  );
}

// One day of the timeline: the date as a plain label, then its reconciliations on a line down
// the left, one marker each.
function DaySection({ day, onOpen }: { day: Day; onOpen: (r: TableReconciliationApiResponse) => void }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="pb-6 last:pb-0">
      <h2 id={headingId} className="type-label-large mb-1 text-on-surface-variant">
        <span className="sr-only">Reconciliations on</span> {day.date}
      </h2>
      <Timeline>
        {folded(day.records).map((line) =>
          line.kind === "fold" ? (
            <FoldLine key={line.records[0]!.reconciliation_id} records={line.records} onOpen={onOpen} />
          ) : (
            <RecordLine key={line.record.reconciliation_id} record={line.record} onOpen={() => onOpen(line.record)} />
          ),
        )}
      </Timeline>
    </section>
  );
}

type Shown =
  | { kind: "record"; record: TableReconciliationApiResponse }
  | { kind: "loading" }
  | { kind: "message"; text: string }
  | { kind: "error"; error: unknown };

function PanelContent({ shown }: { shown: Shown }) {
  switch (shown.kind) {
    case "record":
      return <ReconciliationPanel record={shown.record} />;
    case "loading":
      return <PanelSkeleton label="Loading reconciliation…" />;
    case "message":
      return <p className="type-body-medium text-on-surface-variant">{shown.text}</p>;
    case "error":
      return <Banner type="negative" title={`Could not load the reconciliation: ${errorMessage(shown.error)}`} />;
  }
}

// Each time this table was reconciled, newest first: what woke it, what it decided and what it
// started. A line opens its record in a side panel beside the list (full width and modal on a
// phone), kept in the url as `?reconciliation=<id>`; the full measurements sit one click further
// in. The panel shows the listed record; a record older than the pages loaded is read by its id.
export function ReconciliationsTab({ tableUuid }: { tableUuid: string }) {
  const { openId, open, close } = useOpenRecord("reconciliation");
  const pages = useInfiniteQuery({
    // Under the list's url key, so invalidating getListTableReconciliationsQueryKey(uuid) refetches it.
    queryKey: [...getListTableReconciliationsQueryKey(tableUuid), "pages"],
    queryFn: ({ pageParam, signal }) =>
      listTableReconciliations(tableUuid, pageParam === null ? { limit: PAGE_SIZE } : { before: pageParam, limit: PAGE_SIZE }, { signal }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => (lastPage.length < PAGE_SIZE ? undefined : (lastPage.at(-1)?.reconciled_at ?? undefined)),
  });
  const records = pages.data?.pages.flat();
  const listed = openId === null ? undefined : records?.find((record) => record.reconciliation_id === openId);
  const notInList = openId !== null && records !== undefined && listed === undefined;
  const byId = useGetTableReconciliation(openId ?? "", { query: { enabled: notInList } });

  if (pages.isPending) return <PanelSkeleton label="Loading reconciliations…" />;
  // A failed background read keeps the records it already has on screen; only a first read that fails replaces them.
  if (pages.isError && pages.data === undefined) {
    return <Banner type="negative" title={`Could not load reconciliations: ${errorMessage(pages.error)}`} />;
  }

  const shown: Shown =
    listed !== undefined
      ? { kind: "record", record: listed }
      : byId.data !== undefined
        ? byId.data.table_uuid === tableUuid
          ? { kind: "record", record: byId.data }
          : { kind: "message", text: "This reconciliation belongs to another table" }
        : byId.isError
          ? isGone(byId.error)
            ? { kind: "message", text: "This reconciliation is no longer available" }
            : { kind: "error", error: byId.error }
          : { kind: "loading" };

  const loaded = records ?? [];
  return (
    <>
      {pages.isError && <Banner type="information" title={REFRESH_FAILED} className="mb-4" />}
      {loaded.length === 0 ? (
        <p className="type-body-medium text-on-surface-variant">No reconciliations yet.</p>
      ) : (
        groupedByDay(loaded).map((day) => <DaySection key={day.date} day={day} onOpen={(record) => open(record.reconciliation_id)} />)
      )}
      {pages.hasNextPage && (
        <Button
          styleType="outlined"
          size="small"
          className="mt-4"
          isLoading={pages.isFetchingNextPage}
          onClick={() => void pages.fetchNextPage()}
        >
          Show older
        </Button>
      )}
      <Drawer
        modal={false}
        contentKey={openId ?? undefined}
        isOpen={openId !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) close();
        }}
        title={shown.kind === "record" ? headline(shown.record) : "Reconciliation"}
      >
        <PanelContent shown={shown} />
      </Drawer>
    </>
  );
}
