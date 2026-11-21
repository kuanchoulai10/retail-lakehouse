import { Button, IconChevronDown, IconChevronUp, IconCircleCheck, IconRadar, IconX, StatusBadge, TextLink } from "@retail-lakehouse/design-system";
import { useId, useState } from "react";
import { Link } from "react-router";
import type { ReconciliationOperationApiResponse, TableReconciliationApiResponse } from "@/api/generated/model";
import { RunLink } from "@/components/tabs/RunLink";
import {
  formatMeasured,
  formatRule,
  isManualRun,
  measurementLabel,
  operationLabel,
  policyLabel,
  policyOrigin,
  reasonSentence,
  resultLabel,
  resultOrder,
  wakeText,
} from "@/components/tabs/reconciliationText";
import { formatTimestamp } from "@/format";
import { policyVersionPath } from "@/lib/policyPaths";

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
  // Lines with a threshold carry a met mark; conditions combine with OR, which only matters with two or more.
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
            <p className="text-on-surface-variant">Starts when any marked line holds</p>
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
  const runId = operation.result === "started" ? operation.run_id : null;
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

// What woke the table, the policy it used and, for each operation, what it measured and decided;
// the full measurements sit one click further in.
export function ReconciliationPanel({ record }: { record: TableReconciliationApiResponse }) {
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
          <p className="type-body-small text-on-surface-variant">
            Policy{" "}
            {record.policy_deleted ? (
              <span className="font-mono">{policyLabel(record)}</span>
            ) : (
              <TextLink asChild inline className="font-mono">
                <Link to={policyVersionPath(record.policy_name, record.policy_version)}>{policyLabel(record)}</Link>
              </TextLink>
            )}
            , {policyOrigin(record)}
          </p>
        </div>
      </div>
      {operations.map((operation) => (
        <OperationBlock key={operation.operation} record={record} operation={operation} />
      ))}
    </div>
  );
}
