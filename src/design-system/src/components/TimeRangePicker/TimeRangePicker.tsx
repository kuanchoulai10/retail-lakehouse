import { ToggleGroup } from "radix-ui";
import { cn } from "../../lib/cn";

export type TimeRangeOption = {
  value: string;
  label: string;
  description?: string;
};

export type TimeRangePickerProps = {
  options: readonly TimeRangeOption[];
  value: string;
  onValueChange: (value: string) => void;
  "aria-label"?: string;
  className?: string;
};

export function TimeRangePicker({
  options,
  value,
  onValueChange,
  "aria-label": ariaLabel = "Time range",
  className,
}: TimeRangePickerProps) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(next) => {
        if (next) {
          onValueChange(next);
        }
      }}
      aria-label={ariaLabel}
      className={cn(
        "inline-flex max-w-full overflow-hidden rounded-md border border-outline-dim bg-surface",
        className,
      )}
    >
      {options.map((option) => (
        <ToggleGroup.Item
          key={option.value}
          value={option.value}
          aria-label={option.description ?? option.label}
          className={cn(
            "type-label-large min-h-control min-w-12 cursor-pointer px-3 text-on-surface tabular-nums",
            "not-first:border-l not-first:border-outline-dim hover:bg-hovered-variant",
            "data-[state=on]:bg-selected-surface data-[state=on]:font-bold",
            "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
          )}
        >
          {option.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
