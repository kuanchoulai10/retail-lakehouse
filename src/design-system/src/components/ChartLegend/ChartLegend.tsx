import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type ChartLegendItem = {
  name: string;
  colour: string;
  value?: string;
};

export type ChartLegendProps = Omit<ComponentProps<"ul">, "children"> & {
  items: readonly ChartLegendItem[];
};

export const ChartLegend = forwardRef<HTMLUListElement, ChartLegendProps>(
  ({ items, className, ...rest }, ref) => (
    <ul
      ref={ref}
      aria-label="Legend"
      className={cn("type-body-small flex flex-wrap gap-x-4 gap-y-1 text-on-surface-variant", className)}
      {...rest}
    >
      {items.map((item) => (
        <li key={item.name} className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-2 shrink-0 rounded-xl" style={{ backgroundColor: item.colour }} />
          <span className={item.value === undefined ? undefined : "flex-1"}>{item.name}</span>
          {item.value === undefined ? null : (
            <span className="ml-3 font-bold text-on-surface tabular-nums">{item.value}</span>
          )}
        </li>
      ))}
    </ul>
  ),
);
ChartLegend.displayName = "ChartLegend";
