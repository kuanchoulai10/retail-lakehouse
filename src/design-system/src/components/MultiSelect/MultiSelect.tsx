import { forwardRef, useId } from "react";
import { IconChevronDown } from "../../icons";
import { cn } from "../../lib/cn";
import { fieldControlStyle } from "../../lib/Field";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "../DropdownMenu/DropdownMenu";

export type MultiSelectItem = { value: string; label: string };

export type MultiSelectProps = {
  label: string;
  items: MultiSelectItem[];
  value: string[];
  onValueChange: (value: string[]) => void;
  noneLabel?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
};

export const MultiSelect = forwardRef<HTMLButtonElement, MultiSelectProps>(
  (
    { label, items, value, onValueChange, noneLabel = "None selected", disabled, id, className },
    ref,
  ) => {
    const generatedId = useId();
    const controlId = id ?? generatedId;
    const labelId = `${controlId}-label`;
    const summaryId = `${controlId}-summary`;
    const chosen = items.filter((item) => value.includes(item.value));
    const summary = chosen.length === 0 ? noneLabel : chosen.map((item) => item.label).join(", ");

    const toggle = (itemValue: string, checked: boolean) =>
      onValueChange(
        items.filter((item) => (item.value === itemValue ? checked : value.includes(item.value))).map((item) => item.value),
      );

    return (
      <div className="flex min-w-0 flex-col gap-1">
        <label id={labelId} htmlFor={controlId} className="type-label-large text-on-surface">
          {label}
        </label>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              ref={ref}
              id={controlId}
              type="button"
              disabled={disabled}
              aria-labelledby={`${labelId} ${summaryId}`}
              className={cn(
                fieldControlStyle,
                "flex h-control min-w-0 cursor-pointer items-center justify-between gap-2 text-left",
                className,
              )}
            >
              <span id={summaryId} className="truncate">
                {summary}
              </span>
              <IconChevronDown aria-hidden="true" className="size-6 shrink-0" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="min-w-(--radix-dropdown-menu-trigger-width)">
            {items.map((item) => (
              <DropdownMenuCheckboxItem
                key={item.value}
                checked={value.includes(item.value)}
                onCheckedChange={(checked) => toggle(item.value, checked === true)}
                onSelect={(event) => event.preventDefault()}
              >
                {item.label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  },
);
MultiSelect.displayName = "MultiSelect";
