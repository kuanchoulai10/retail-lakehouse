import { DescriptionList, type DescriptionListItem, Timeline, TimelineItem } from "@retail-lakehouse/design-system";
import { type ReactNode, useId } from "react";
import type { TableMaintenanceRunApiResponse, TableMaintenanceRunAttemptApiResponse } from "@/api/generated/model";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import { formatDuration, formatTimestamp } from "@/format";
import { eventLogText, failureClassText, nextStepText, queueWaitText, runTimeText } from "@/lib/attemptText";
import { compactionScopeText } from "@/lib/compactionScopeText";
import { isInFlightStatus } from "@/lib/isInFlightStatus";

function timeText(value: string | null): string {
  return value === null ? "—" : formatTimestamp(value);
}

// Each key in monospace with its JSON value: what the run was set to do, or the numbers it returned.
function KeyValues({ values }: { values: Record<string, unknown> }) {
  return (
    <ul className="flex flex-col gap-1">
      {Object.entries(values).map(([key, value]) => (
        <li key={key} className="break-all">
          <span className="font-mono">{key}</span>: <span className="font-mono">{JSON.stringify(value)}</span>
        </li>
      ))}
    </ul>
  );
}

function fields(run: TableMaintenanceRunApiResponse): DescriptionListItem[] {
  const scope = compactionScopeText(run);
  const items: DescriptionListItem[] = [
    { term: "Run", description: <span className="font-mono">{run.run_id}</span> },
    { term: "Status", description: <RunStatusBadge status={run.status} /> },
    { term: "Trigger", description: run.trigger },
    { term: "Priority", description: run.priority },
    { term: "Started", description: timeText(run.started_at) },
    { term: "Finished", description: timeText(run.finished_at) },
    {
      term: "Duration",
      description: <span className="tabular-nums">{run.started_at === null ? "—" : formatDuration(run.started_at, run.finished_at)}</span>,
    },
  ];
  if (scope !== null) {
    items.push({
      term: "Scope",
      description: (
        <>
          {scope.summary}
          {scope.partitions.length > 0 && (
            <ul className="type-code text-on-surface-variant">
              {scope.partitions.map(({ specId, text }) => (
                <li key={`${specId}:${text}`} className="break-all">{`spec ${specId}: ${text}`}</li>
              ))}
            </ul>
          )}
        </>
      ),
    });
  }
  if (Object.keys(run.settings).length > 0) {
    items.push({ term: "Settings", description: <KeyValues values={run.settings} /> });
  }
  if (Object.keys(run.metrics).length > 0) {
    items.push({ term: "Result", description: <KeyValues values={run.metrics} /> });
  }
  if (run.error !== null) {
    items.push({ term: "Error", description: <span className="text-negative-text">{run.error}</span> });
  }
  if (run.skip_reason !== null) {
    items.push({ term: "Skipped", description: run.skip_reason });
  }
  items.push({ term: "Execution", description: <span className="font-mono break-all">{run.execution_ref}</span> });
  return items;
}

// What the attempt's record says, one line each: how long it queued and ran, why it failed, what
// the platform did next, whether its Spark event log finished and the job it ran as.
function attemptLines(attempt: TableMaintenanceRunAttemptApiResponse, now: Date): ReactNode {
  // Each line is keyed by what it tells, so a counter that moves does not remount its line.
  const lines = [
    { key: "queued", text: `Queued ${queueWaitText(attempt, now)}` },
    { key: "ran", text: `Ran ${runTimeText(attempt, now)}` },
    { key: "failure", text: failureClassText(attempt.failure_class) },
    { key: "next", text: nextStepText(attempt.next_step, attempt.next_size) },
    { key: "event-log", text: `Event log: ${eventLogText(attempt.event_log_finished)}` },
  ].filter((line) => line.text !== "");
  return (
    <>
      {lines.map((line) => (
        <span key={line.key} className="block tabular-nums">
          {line.text}
        </span>
      ))}
      {attempt.job_name !== null && <span className="block font-mono break-all">{attempt.job_name}</span>}
    </>
  );
}

// One maintenance run: its fields, then its attempts as a timeline, oldest first. The attempt in
// flight (queued or running) has the filled marker, as the entry under way; the ended ones are outlined.
// The times of a queued or running attempt count up to `now`.
export function MaintenanceRunPanel({ run, now }: { run: TableMaintenanceRunApiResponse; now: Date }) {
  const attemptsHeadingId = useId();
  return (
    <div className="flex flex-col gap-6">
      <DescriptionList items={fields(run)} />
      <section aria-labelledby={attemptsHeadingId} className="flex flex-col gap-2">
        <h3 id={attemptsHeadingId} className="type-title-small text-on-surface">
          Attempts
        </h3>
        {run.attempts.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">
            {run.status === "pending" ? "No attempt yet. This run waits for the runs before it." : "No attempt."}
          </p>
        ) : (
          <Timeline aria-labelledby={attemptsHeadingId}>
            {run.attempts.map((attempt) => (
              <TimelineItem
                key={attempt.attempt}
                marker={isInFlightStatus(attempt.status) ? "filled" : "outlined"}
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    <span>{`Attempt ${attempt.attempt} · ${attempt.size}`}</span>
                    <RunStatusBadge status={attempt.status} />
                  </span>
                }
                description={attemptLines(attempt, now)}
              />
            ))}
          </Timeline>
        )}
      </section>
    </div>
  );
}
