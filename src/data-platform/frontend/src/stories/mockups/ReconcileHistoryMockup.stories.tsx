// Throwaway mockup for the reconcile-history discussion (2026-11-10). Not product code; delete
// once the design is agreed.
import {
  Badge,
  Button,
  Drawer,
  IconChevronDown,
  IconChevronRight,
  IconChevronUp,
  IconCircleCheck,
  IconRadar,
  StatusBadge,
  TextLink,
  TooltipProvider,
} from "@retail-lakehouse/design-system";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

type Metric = { name: string; observed: string; rule: string; met: boolean };

type Result =
  | { kind: "triggered"; runId: string }
  | { kind: "would-trigger" }
  | { kind: "below" }
  | { kind: "cooldown"; until: string }
  | { kind: "disabled" }
  | { kind: "waiting"; behind: string };

type OperationCheck = {
  operation: string;
  combine: "all" | "any";
  metrics: Metric[];
  result: Result;
};

type Reconcile = {
  id: string;
  day: string;
  time: string;
  ago: string;
  woken: string;
  wokenDetail?: string;
  dryRun?: boolean;
  checks: OperationCheck[];
};

const IDLE: Metric = { name: "Partitions idle for 1 h", observed: "6 of 9", rule: "at least 1", met: true };

function quiet(id: string, time: string, ago: string): Reconcile {
  return {
    id,
    day: "Nov 10, 2026",
    time,
    ago,
    woken: "Schedule",
    wokenDetail: "every 1 h",
    checks: [
      {
        operation: "Rewrite data files",
        combine: "all",
        metrics: [
          { name: "Small files per partition", observed: "380", rule: "> 500", met: false },
          { name: "Average file size", observed: "42 MB", rule: "< 128 MB", met: true },
          IDLE,
        ],
        result: { kind: "below" },
      },
      {
        operation: "Rewrite manifests",
        combine: "any",
        metrics: [
          { name: "Small manifests", observed: "12", rule: "≥ 20", met: false },
          { name: "Manifests per snapshot", observed: "40", rule: "> 100", met: false },
        ],
        result: { kind: "below" },
      },
      {
        operation: "Expire snapshots",
        combine: "any",
        metrics: [
          { name: "Snapshots", observed: "301", rule: "> 1,000", met: false },
          { name: "Oldest snapshot age", observed: "2 d", rule: "> 7 d", met: false },
        ],
        result: { kind: "below" },
      },
      { operation: "Remove orphan files", combine: "all", metrics: [], result: { kind: "disabled" } },
    ],
  };
}

const RECONCILES: Reconcile[] = [
  {
    id: "r-109",
    day: "Nov 10, 2026",
    time: "10:42",
    ago: "12 min ago",
    woken: "Catalog commit",
    wokenDetail: "3 commits within the 5 min debounce",
    checks: [
      {
        operation: "Rewrite data files",
        combine: "all",
        metrics: [
          { name: "Small files per partition", observed: "1,240", rule: "> 500", met: true },
          { name: "Average file size", observed: "18 MB", rule: "< 128 MB", met: true },
          IDLE,
        ],
        result: { kind: "triggered", runId: "run-42" },
      },
      {
        operation: "Rewrite manifests",
        combine: "any",
        metrics: [
          { name: "Small manifests", observed: "42", rule: "≥ 20", met: true },
          { name: "Manifests per snapshot", observed: "61", rule: "> 100", met: false },
        ],
        result: { kind: "waiting", behind: "Rewrite data files" },
      },
      {
        operation: "Expire snapshots",
        combine: "any",
        metrics: [
          { name: "Snapshots", observed: "312", rule: "> 1,000", met: false },
          { name: "Oldest snapshot age", observed: "2 d", rule: "> 7 d", met: false },
        ],
        result: { kind: "below" },
      },
      {
        operation: "Remove orphan files",
        combine: "all",
        metrics: [{ name: "Since last run", observed: "3 d", rule: "≥ 7 d", met: false }],
        result: { kind: "cooldown", until: "Nov 14, 03:00" },
      },
    ],
  },
  quiet("r-108", "09:42", "1 h ago"),
  quiet("r-107", "08:42", "2 h ago"),
  quiet("r-106", "07:42", "3 h ago"),
  quiet("r-105", "06:42", "4 h ago"),
  {
    ...quiet("r-104", "05:42", "5 h ago"),
    dryRun: true,
    checks: [
      {
        operation: "Rewrite data files",
        combine: "all",
        metrics: [
          { name: "Small files per partition", observed: "620", rule: "> 500", met: true },
          { name: "Average file size", observed: "30 MB", rule: "< 128 MB", met: true },
          IDLE,
        ],
        result: { kind: "would-trigger" },
      },
      ...quiet("x", "", "").checks.slice(1),
    ],
  },
];

const started = (r: Reconcile) =>
  r.checks.filter((c) => c.result.kind === "triggered" || c.result.kind === "would-trigger");

const isQuiet = (r: Reconcile) => started(r).length === 0;

function headline(r: Reconcile): string {
  const ops = started(r).map((c) => c.operation);
  if (ops.length === 0) return "Nothing to do";
  return r.dryRun ? `Would start ${ops.join(", ")}` : `Started ${ops.join(", ")}`;
}

// ---------- list ----------

function ReconcileRow({ reconcile, onOpen }: { reconcile: Reconcile; onOpen: () => void }) {
  const ops = started(reconcile);
  const active = ops.length > 0;
  return (
    <li className="relative flex gap-3 py-3 pl-9">
      <span
        className={
          "absolute left-2 top-4 flex size-3 rounded-full border-2 " +
          (active ? "border-primary bg-primary" : "border-outline-dim bg-surface")
        }
      />
      <div className="min-w-0 flex-1">
        <p className="type-label-large text-on-surface">
          <button type="button" className="text-left hover:underline" onClick={onOpen}>
            {headline(reconcile)}
          </button>
          {reconcile.dryRun && <Badge className="ml-2">Dry run</Badge>}
        </p>
        <p className="type-body-small text-on-surface-variant">
          {reconcile.woken} at {reconcile.time}, {reconcile.ago}
        </p>
      </div>
      {ops.map((c) =>
        c.result.kind === "triggered" ? (
          <TextLink key={c.operation} href="#" className="type-body-small self-center whitespace-nowrap">
            {c.result.runId}
          </TextLink>
        ) : null,
      )}
    </li>
  );
}

function QuietGroup({ items, onOpen }: { items: Reconcile[]; onOpen: (r: Reconcile) => void }) {
  const [open, setOpen] = useState(false);
  const first = items[items.length - 1];
  const last = items[0];
  return (
    <li className="relative py-2 pl-9">
      <span className="absolute left-2 top-3.5 flex size-3 rounded-full border-2 border-dashed border-outline-dim bg-surface" />
      <button
        type="button"
        aria-expanded={open}
        className="type-body-small flex items-center gap-1 text-on-surface-variant hover:text-on-surface"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
        {items.length} checks found nothing to do, {first?.time}–{last?.time}
      </button>
      {open && (
        <ul className="mt-1">
          {items.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className="type-body-small py-1 pl-5 text-on-surface-variant hover:text-on-surface hover:underline"
                onClick={() => onOpen(r)}
              >
                {r.woken} at {r.time}
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

// ---------- detail ----------

function resultBadge(result: Result) {
  switch (result.kind) {
    case "triggered":
      return <StatusBadge status="notice">Started</StatusBadge>;
    case "would-trigger":
      return <StatusBadge status="notice">Would start</StatusBadge>;
    case "waiting":
      return <StatusBadge status="neutral">Waiting</StatusBadge>;
    case "below":
      return <StatusBadge status="neutral">Not needed</StatusBadge>;
    case "cooldown":
      return <StatusBadge status="neutral">Cooling down</StatusBadge>;
    case "disabled":
      return <StatusBadge status="neutral">Off</StatusBadge>;
  }
}

// One sentence that says why, citing only the measurements that decided it.
function reason(check: OperationCheck): string {
  const met = check.metrics.filter((m) => m.met);
  const unmet = check.metrics.filter((m) => !m.met);
  const say = (m: Metric) => `${m.name.toLowerCase()} ${m.observed} (${m.rule})`;
  switch (check.result.kind) {
    case "triggered":
    case "would-trigger":
      return `Because ${met.map(say).join(" and ")}.`;
    case "waiting":
      return `Needed (${met.map(say).join(", ")}), runs after ${check.result.behind} finishes.`;
    case "below":
      return check.combine === "all"
        ? `Not yet: ${unmet.map(say).join(", ")}.`
        : `Not yet: ${check.metrics.map(say).join(", ")}.`;
    case "cooldown":
      return `Ran recently; next allowed ${check.result.until}.`;
    case "disabled":
      return "Turned off in this table's settings.";
  }
}

function OperationBlock({ check }: { check: OperationCheck }) {
  const [showAll, setShowAll] = useState(false);
  return (
    <section className="flex flex-col gap-1 border-l-2 border-outline pl-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="type-label-large text-on-surface">{check.operation}</h3>
        {resultBadge(check.result)}
      </div>
      <p className="type-body-small text-on-surface-variant">{reason(check)}</p>
      {check.result.kind === "triggered" && (
        <TextLink href="#" className="type-body-small">
          Open maintenance run {check.result.runId}
        </TextLink>
      )}
      {check.metrics.length > 0 && (
        <button
          type="button"
          aria-expanded={showAll}
          className="type-body-small flex items-center gap-1 self-start text-on-surface-variant hover:text-on-surface"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
          {showAll ? "Hide measurements" : "All measurements"}
        </button>
      )}
      {showAll && (
        <dl className="type-body-small mt-1 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          <p className="col-span-2 text-on-surface-variant">
            {check.combine === "all" ? "Starts when every line holds" : "Starts when any line holds"}
          </p>
          {check.metrics.map((m) => (
            <div key={m.name} className="contents">
              <dt className="flex items-center gap-1 text-on-surface-variant">
                {m.met ? <IconCircleCheck size={14} className="text-primary" /> : <span className="inline-block w-3.5" />}
                {m.name}
              </dt>
              <dd className="tabular-nums text-on-surface">
                {m.observed} <span className="text-on-surface-variant">/ {m.rule}</span>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function ReconcileDetail({ reconcile }: { reconcile: Reconcile }) {
  const order = (c: OperationCheck) =>
    ["triggered", "would-trigger", "waiting", "below", "cooldown", "disabled"].indexOf(c.result.kind);
  const checks = [...reconcile.checks].sort((a, b) => order(a) - order(b));
  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-2">
        <IconRadar className="mt-0.5 shrink-0 text-on-surface-variant" size={18} />
        <div>
          <p className="type-body-medium text-on-surface">
            Woken by {reconcile.woken.toLowerCase()}
            {reconcile.wokenDetail && <span className="text-on-surface-variant"> ({reconcile.wokenDetail})</span>}
          </p>
          <p className="type-body-small text-on-surface-variant">
            {reconcile.day}, {reconcile.time}
            {reconcile.dryRun && " · dry run, nothing was started"}
          </p>
        </div>
      </div>
      {checks.map((check) => (
        <OperationBlock key={check.operation} check={check} />
      ))}
    </div>
  );
}

// ---------- page ----------

function groupQuiet(list: Reconcile[]): (Reconcile | Reconcile[])[] {
  const out: (Reconcile | Reconcile[])[] = [];
  for (const r of list) {
    const prev = out[out.length - 1];
    if (isQuiet(r) && Array.isArray(prev)) prev.push(r);
    else out.push(isQuiet(r) ? [r] : r);
  }
  return out.map((x) => (Array.isArray(x) && x.length === 1 ? x[0]! : x));
}

function ReconcileHistoryMockup() {
  const [selected, setSelected] = useState<Reconcile | null>(null);
  return (
    <TooltipProvider>
      <div className="max-w-3xl p-6">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="type-title-small text-on-surface">Maintenance checks</h2>
            <p className="type-body-small text-on-surface-variant">
              Each time this table was checked, and what it started.
            </p>
          </div>
          <Button styleType="outlined" size="small">
            Check now
          </Button>
        </div>
        <h3 className="type-label-large mb-1 text-on-surface-variant">Nov 10, 2026</h3>
        <ul className="relative before:absolute before:bottom-3 before:left-3.25 before:top-3 before:w-px before:bg-outline">
          {groupQuiet(RECONCILES).map((item) =>
            Array.isArray(item) ? (
              <QuietGroup key={item[0]!.id} items={item} onOpen={setSelected} />
            ) : (
              <ReconcileRow key={item.id} reconcile={item} onOpen={() => setSelected(item)} />
            ),
          )}
        </ul>
      </div>
      <Drawer
        isOpen={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
        title={selected ? headline(selected) : ""}
      >
        {selected && <ReconcileDetail reconcile={selected} />}
      </Drawer>
    </TooltipProvider>
  );
}

const meta = {
  title: "Mockups/Reconcile history",
  component: ReconcileHistoryMockup,
  parameters: { layout: "fullscreen" },
  tags: ["!test"],
} satisfies Meta<typeof ReconcileHistoryMockup>;

export default meta;

export const Mockup: StoryObj<typeof meta> = {};
