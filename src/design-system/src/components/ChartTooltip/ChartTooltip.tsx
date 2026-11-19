import { formatChartNumber } from "../../lib/chart/formatChartNumber";

export type ChartTooltipEntry = {
  name?: unknown;
  value?: unknown;
  color?: string;
  dataKey?: unknown;
};

export type ChartTooltipProps = {
  active?: boolean;
  label?: unknown;
  payload?: readonly ChartTooltipEntry[];
  valueFormatter?: (value: number) => string;
  labelFormatter?: (label: unknown) => string;
};

export function ChartTooltip({
  active,
  label,
  payload,
  valueFormatter = formatChartNumber,
  labelFormatter = String,
}: ChartTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  return (
    <div
      data-chart-tooltip=""
      className="type-body-small min-w-32 rounded-sm bg-inverse-surface px-2 py-1.5 text-inverse-on-surface"
    >
      {label === undefined ? null : <p className="mb-1 font-bold">{labelFormatter(label)}</p>}
      <ul className="flex flex-col gap-0.5">
        {payload.map((entry) => (
          <li key={String(entry.dataKey ?? entry.name)} className="flex items-center gap-2">
            <span aria-hidden="true" className="size-2 shrink-0 rounded-xl" style={{ backgroundColor: entry.color }} />
            <span className="flex-1">{String(entry.name)}</span>
            <span className="font-bold tabular-nums">
              {typeof entry.value === "number" ? valueFormatter(entry.value) : String(entry.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
