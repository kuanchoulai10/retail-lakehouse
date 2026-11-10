import {
  Badge,
  Banner,
  Button,
  Drawer,
  IconChevronDown,
  IconChevronRight,
  IconChevronUp,
  IconCircleCheck,
  IconRadar,
  IconX,
  StatusBadge,
  TextLink,
  Timeline,
  TimelineItem,
} from "@retail-lakehouse/design-system";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Link } from "react-router";
import type {
  ReconciliationOperationApiResponse,
  TableReconciliationApiResponse,
} from "@/api/generated/model";
import {
  getListTableReconciliationsQueryKey,
  listTableReconciliations,
} from "@/api/generated/table-reconciliations/table-reconciliations";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import {
  formatMeasured,
  formatRule,
  headline,
  isManualRun,
  foldKey,
  foldText,
  formatTime,
  mainWakeText,
  measurementLabel,
  operationLabel,
  reasonSentence,
  resultLabel,
  resultOrder,
  wakeText,
} from "@/components/tabs/reconciliationText";
import { errorMessage, formatRelativeTime, formatTimestamp } from "@/format";

const PAGE_SIZE = 50;

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

function runPath(runId: string): string {
  return `../maintenance?run=${encodeURIComponent(runId)}`;
}

// Shows the run id's first 8 characters; the accessible name carries the whole id.
function RunLink({ runId, label, className }: { runId: string; label: string; className?: string }) {
  return (
    <TextLink asChild className={className}>
      <Link to={runPath(runId)} relative="path" aria-label={`Open maintenance run ${runId}`}>
        {label} <span className="font-mono">{runId.slice(0, 8)}</span>
      </Link>
    </TextLink>
  );
}

function startedRun(r: TableReconciliationApiResponse): string | null {
  return r.run_id !== null && r.operations.some((op) => op.result === "started") ? r.run_id : null;
}

// Filled when the reconciliation started, or in dry run would have started, something.
function startedSomething(r: TableReconciliationApiResponse): boolean {
  return r.operations.some((op) => op.result === "started" || op.result === "would_start");
}

function RecordLine({ record, onOpen }: { record: TableReconciliationApiResponse; onOpen: () => void }) {
  const runId = startedRun(record);
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

function MetMark({ met }: { met: boolean | null }) {
  if (met === null) return <span aria-hidden="true" className="inline-block w-3.5 shrink-0" />;
  return met ? (
    <>
      <IconCircleCheck aria-hidden="true" size={14} className="shrink-0 text-on-surface-variant" />
      <span className="sr-only">Met:</span>
    </>
  ) : (
    <>
      <IconX aria-hidden="true" size={14} className="shrink-0 text-on-surface-variant" />
      <span className="sr-only">Not met:</span>
    </>
  );
}

function AllMeasurements({ operation }: { operation: ReconciliationOperationApiResponse }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const label = operationLabel(operation.operation);
  // Lines with a threshold carry a met mark; the combine rule only matters with two or more.
  const deciding = operation.measurements.filter((m) => m.threshold !== null).length;
  return (
    <>
      <Button
        styleType="ghost"
        size="small"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        className="self-start"
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <IconChevronUp aria-hidden="true" size={14} /> : <IconChevronDown aria-hidden="true" size={14} />}
        All measurements
      </Button>
      {open && (
        <div id={listId} className="type-body-small flex flex-col gap-1">
          {deciding > 1 && (
            <p className="text-on-surface-variant">
              {operation.combine === "any" ? "Starts when any marked line holds" : "Starts when every marked line holds"}
            </p>
          )}
          <ul aria-label={`All measurements of ${label}`} className="flex flex-col gap-1">
            {operation.measurements.map((m) => (
              <li key={m.key} className="flex items-center justify-between gap-4">
                <span className="flex min-w-0 items-center gap-1 text-on-surface-variant">
                  <MetMark met={m.met} />
                  {measurementLabel(m.key)}
                </span>
                <span className="shrink-0 tabular-nums text-on-surface">
                  {formatMeasured(m.observed, m.unit)}
                  {m.threshold !== null && <span className="text-on-surface-variant"> / {formatRule(m)}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function OperationBlock({ record, operation }: { record: TableReconciliationApiResponse; operation: ReconciliationOperationApiResponse }) {
  const headingId = useId();
  const status = operation.result === "started" || operation.result === "would_start" ? "notice" : "neutral";
  const runId = operation.result === "started" ? startedRun(record) : null;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-1 border-l-2 border-outline pl-4">
      <div className="flex items-center justify-between gap-2">
        <h3 id={headingId} className="type-label-large text-on-surface">
          {operationLabel(operation.operation)}
        </h3>
        <StatusBadge status={status}>{resultLabel(operation.result)}</StatusBadge>
      </div>
      <p className="type-body-small text-on-surface-variant">{reasonSentence(operation, { manualRun: isManualRun(record) })}</p>
      {runId !== null && <RunLink runId={runId} label="Open maintenance run" className="type-body-small self-start" />}
      {operation.measurements.length > 0 && <AllMeasurements operation={operation} />}
    </section>
  );
}

function ReconciliationDetail({ record }: { record: TableReconciliationApiResponse }) {
  const operations = [...record.operations].sort((a, b) => resultOrder(a.result) - resultOrder(b.result));
  const manual = isManualRun(record);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-2">
        <IconRadar aria-hidden="true" className="mt-0.5 shrink-0 text-on-surface-variant" size={18} />
        <div>
          <p className="type-body-medium text-on-surface">Woken by {wakeText(record)}</p>
          <p className="type-body-small text-on-surface-variant">
            <time dateTime={record.reconciled_at}>{formatTimestamp(record.reconciled_at)}</time>
            {record.dry_run && (manual ? " · dry run is on; a manual run still runs" : " · dry run, nothing was started")}
          </p>
        </div>
      </div>
      {operations.map((operation) => (
        <OperationBlock key={operation.operation} record={record} operation={operation} />
      ))}
    </div>
  );
}

// Each time this table was reconciled, newest first: what woke it, what it decided and what it
// started. Details open in a drawer; the full measurements sit one click further in.
export function ReconciliationsTab({ tableUuid }: { tableUuid: string }) {
  // The drawer keeps showing the last record it opened while it closes, so it never empties mid-way.
  const [shown, setShown] = useState<TableReconciliationApiResponse | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const open = (record: TableReconciliationApiResponse) => {
    setShown(record);
    setIsOpen(true);
  };
  const pages = useInfiniteQuery({
    // Under the list's url key, so invalidating getListTableReconciliationsQueryKey(uuid) refetches it.
    queryKey: [...getListTableReconciliationsQueryKey(tableUuid), "pages"],
    queryFn: ({ pageParam, signal }) =>
      listTableReconciliations(tableUuid, pageParam === null ? { limit: PAGE_SIZE } : { before: pageParam, limit: PAGE_SIZE }, { signal }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => (lastPage.length < PAGE_SIZE ? undefined : (lastPage.at(-1)?.reconciled_at ?? undefined)),
  });

  if (pages.isPending) return <PanelSkeleton label="Loading reconciliations…" />;
  if (pages.isError) {
    return <Banner type="negative" title={`Could not load reconciliations: ${errorMessage(pages.error)}`} />;
  }
  const records = pages.data.pages.flat();
  if (records.length === 0) {
    return <p className="type-body-medium text-on-surface-variant">No reconciliations yet.</p>;
  }
  return (
    <>
      {groupedByDay(records).map((day) => (
        <DaySection key={day.date} day={day} onOpen={open} />
      ))}
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
      <Drawer isOpen={isOpen} onOpenChange={setIsOpen} title={shown ? headline(shown) : ""}>
        {shown && <ReconciliationDetail record={shown} />}
      </Drawer>
    </>
  );
}
