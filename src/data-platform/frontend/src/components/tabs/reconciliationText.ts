import type {
  ReconciliationMeasurementApiResponse,
  ReconciliationOperationApiResponse,
  TableReconciliationApiResponse,
} from "@/api/generated/model";
import { formatBytes, formatCount, formatSeconds } from "@/format";

// What a reconciliation's record says, in words: the line headline, the wake reasons and one
// reason sentence per operation. Built from the structured record so the wording can change
// without a migration (spec, "The reason sentence is not stored").

// The order the drawer lists operation blocks in: what happened first, what did not last.
export const RESULT_ORDER = [
  "started",
  "would_start",
  "start_failed",
  "not_needed",
  "cooling_down",
  "off",
  "not_checked",
] as const;

const RESULT_LABELS: Record<string, string> = {
  started: "Started",
  would_start: "Would start",
  start_failed: "Could not start",
  not_needed: "Not needed",
  cooling_down: "Cooling down",
  off: "Off",
  not_checked: "Not checked",
};

// The order wake reasons are defined in; it breaks ties between equally frequent reasons.
const WAKE_REASONS: [string, string][] = [
  ["schedule", "Schedule"],
  ["catalog_commit", "Catalog commit"],
  ["discovery_scan", "Discovery scan"],
  ["settings_changed", "Settings changed"],
  ["resumed", "Resumed"],
  ["paused", "Paused"],
  ["manual_run", "Manual run"],
  ["reconcile_now", "Reconcile now"],
  ["previous_run_finished", "Previous run finished"],
];

const OPERATION_LABELS: Record<string, string> = {
  rewrite_data_files: "Rewrite data files",
  rewrite_manifests: "Rewrite manifests",
  expire_snapshots: "Expire snapshots",
  remove_orphan_files: "Remove orphan files",
};

const MEASUREMENT_LABELS: Record<string, string> = {
  reducible_files: "Reducible files",
  target_file_size: "Target file size",
  qualifying_partitions: "Qualifying partitions",
  small_manifests: "Small manifests",
  expirable_snapshots: "Expirable snapshots",
};

const COMPARISON_SYMBOLS: Record<string, string> = { ">=": "≥", ">": ">", "<": "<", "<=": "≤" };

const NEXT_ALLOWED_FORMAT = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function sentenceCase(key: string): string {
  const words = key.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function operationLabel(operation: string): string {
  return OPERATION_LABELS[operation] ?? sentenceCase(operation);
}

export function resultLabel(result: string): string {
  return RESULT_LABELS[result] ?? sentenceCase(result);
}

export function measurementLabel(key: string): string {
  return MEASUREMENT_LABELS[key] ?? sentenceCase(key);
}

export function formatMeasured(value: number, unit: string): string {
  switch (unit) {
    case "bytes":
      return formatBytes(value);
    case "seconds":
      return formatSeconds(value);
    default:
      return formatCount(value);
  }
}

// "≥ 5", or "" for a context measurement, which has no threshold.
export function formatRule(m: ReconciliationMeasurementApiResponse): string {
  if (m.threshold === null || m.comparison === null) return "";
  return `${COMPARISON_SYMBOLS[m.comparison] ?? m.comparison} ${formatMeasured(m.threshold, m.unit)}`;
}

export function resultOrder(result: string): number {
  const index = (RESULT_ORDER as readonly string[]).indexOf(result);
  return index === -1 ? RESULT_ORDER.length : index;
}

export function isManualRun(r: TableReconciliationApiResponse): boolean {
  return (r.wake_reasons.manual_run ?? 0) > 0;
}

function withResult(r: TableReconciliationApiResponse, result: string): string[] {
  return r.operations.filter((op) => op.result === result).map((op) => operationLabel(op.operation));
}

const TIME_FORMAT = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

export function formatTime(iso: string): string {
  return TIME_FORMAT.format(new Date(iso));
}

function skipText(r: TableReconciliationApiResponse): string {
  return `skipped: table ${(r.skip_reason ?? "skipped").replaceAll("_", " ")}`;
}

// Started, would start or failed to start nothing.
function startedNothing(r: TableReconciliationApiResponse): boolean {
  return !r.operations.some((op) => ["started", "would_start", "start_failed"].includes(op.result));
}

// Consecutive reconciliations with the same fold key fold into one line, so hourly passes that
// did nothing, or an hourly skip of a paused table, do not drown the ones that did something.
// null: the reconciliation did something and always gets its own line.
export function foldKey(r: TableReconciliationApiResponse): string | null {
  return startedNothing(r) ? headline(r) : null;
}

// "{n} reconciliations found nothing to do, {first}–{last}" for records newest first, or
// "{n} reconciliations skipped: table paused, …" for a stretch of skips.
export function foldText(records: TableReconciliationApiResponse[]): string {
  const newest = records[0];
  const oldest = records.at(-1);
  if (newest === undefined || oldest === undefined) return "";
  const what = newest.outcome === "skipped" ? skipText(newest) : "found nothing to do";
  return `${records.length} reconciliations ${what}, ${formatTime(oldest.reconciled_at)}–${formatTime(newest.reconciled_at)}`;
}

export function headline(r: TableReconciliationApiResponse): string {
  if (r.outcome === "skipped") {
    const text = skipText(r);
    return text.charAt(0).toUpperCase() + text.slice(1);
  }
  const parts: string[] = [];
  const started = withResult(r, "started");
  if (started.length > 0) {
    const note = r.dry_run && isManualRun(r) ? " (manual run, dry run is on)" : "";
    parts.push(`Started ${started.join(", ")}${note}`);
  }
  const wouldStart = withResult(r, "would_start");
  if (wouldStart.length > 0) parts.push(`Would start ${wouldStart.join(", ")}`);
  const failed = withResult(r, "start_failed");
  if (failed.length > 0) parts.push(`Could not start ${failed.join(", ")}`);
  return parts.length > 0 ? parts.join("; ") : "Nothing to do";
}

// Each wake reason with its count, the most frequent first, ties in the order reasons are defined.
export function wakeReasons(r: TableReconciliationApiResponse): { label: string; count: number }[] {
  const known = WAKE_REASONS.filter(([reason]) => (r.wake_reasons[reason] ?? 0) > 0).map(([reason, label]) => ({
    label,
    count: r.wake_reasons[reason] ?? 0,
  }));
  const unknown = Object.entries(r.wake_reasons)
    .filter(([reason, count]) => count > 0 && !WAKE_REASONS.some(([k]) => k === reason))
    .map(([reason, count]) => ({ label: sentenceCase(reason), count }));
  return [...known, ...unknown].sort((a, b) => b.count - a.count);
}

function wakeLabel({ label, count }: { label: string; count: number }): string {
  return count > 1 ? `${label} × ${count}` : label;
}

export function mainWakeText(r: TableReconciliationApiResponse): string {
  const main = wakeReasons(r)[0];
  return main === undefined ? "Unknown" : wakeLabel(main);
}

export function wakeText(r: TableReconciliationApiResponse): string {
  return wakeReasons(r).map(wakeLabel).join(", ");
}

// "reducible files 1,240 (needs ≥ 5)". In partition scope the observed value is a sum over the
// qualifying partitions while the threshold applies to each one, so it says so instead of
// implying the sum was compared with the threshold.
function cite(m: ReconciliationMeasurementApiResponse, op: ReconciliationOperationApiResponse): string {
  const name = measurementLabel(m.key).toLowerCase();
  const observed = formatMeasured(m.observed, m.unit);
  const partitions = op.measurements.find((other) => other.key === "qualifying_partitions");
  if (m.key === "reducible_files" && partitions !== undefined) {
    const count = partitions.observed;
    return `${name} ${observed} across ${formatCount(count)} ${count === 1 ? "partition" : "partitions"} (needs ${formatRule(m)} per partition)`;
  }
  return `${name} ${observed} (needs ${formatRule(m)})`;
}

function deciding(op: ReconciliationOperationApiResponse): ReconciliationMeasurementApiResponse[] {
  return op.measurements.filter((m) => m.threshold !== null);
}

function citeAll(ms: ReconciliationMeasurementApiResponse[], op: ReconciliationOperationApiResponse): string {
  return ms.map((m) => cite(m, op)).join(" and ");
}

// The deciding measurements that kept it from being due: for "all" the unmet ones; for "any"
// every one when none was met, and none as soon as one was.
function holdingBack(op: ReconciliationOperationApiResponse): ReconciliationMeasurementApiResponse[] {
  const ms = deciding(op);
  if (op.combine === "any") return ms.some((m) => m.met === true) ? [] : ms;
  return ms.filter((m) => m.met !== true);
}

function nextAllowed(op: ReconciliationOperationApiResponse): string {
  return op.next_eligible_at === null ? "" : `next allowed ${NEXT_ALLOWED_FORMAT.format(new Date(op.next_eligible_at))}`;
}

// One sentence saying why, citing only the measurements that decide; context measurements are
// left out. A manual run assesses nothing, so the caller says when the record is one.
export function reasonSentence(op: ReconciliationOperationApiResponse, { manualRun = false } = {}): string {
  const met = deciding(op).filter((m) => m.met === true);
  switch (op.result) {
    case "started":
    case "would_start":
      if (manualRun) return "Asked for in a manual run.";
      return met.length > 0 ? `Because ${citeAll(met, op)}.` : "Due whenever its cooldown allows.";
    case "start_failed":
      return met.length > 0
        ? `Due: ${citeAll(met, op)}, but the run could not be started.`
        : "Due, but the run could not be started.";
    case "not_needed": {
      const held = holdingBack(op);
      return held.length > 0 ? `Not yet: ${citeAll(held, op)}.` : "Not needed.";
    }
    case "cooling_down": {
      const when = nextAllowed(op);
      const held = holdingBack(op);
      if (held.length > 0) return `Not yet: ${citeAll(held, op)}${when ? `; ${when}` : ""}.`;
      if (met.length > 0) return `Due: ${citeAll(met, op)}, but it ran recently${when ? `; ${when}` : ""}.`;
      return when ? `Ran recently; ${when}.` : "Ran recently.";
    }
    case "off":
      return "Turned off in this table's settings.";
    case "not_checked":
      return "Not part of this manual run.";
    default:
      return resultLabel(op.result);
  }
}
