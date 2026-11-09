import { Popover as PopoverPrimitive } from "radix-ui";
import { forwardRef, useId, useRef, useState, type ReactNode } from "react";
import { DayPicker, type ClassNames, type Matcher } from "react-day-picker";
import { IconArrowRight, IconCalendar, IconChevronLeft, IconChevronRight, IconX } from "../../icons";
import { cn } from "../../lib/cn";
import { FieldFrame, fieldControlStyle, type FieldProps } from "../../lib/Field";

export type DateRange = { from: Date; to?: Date };

type DatePickerBaseProps = FieldProps & {
  id?: string;
  className?: string;
  disabled?: boolean;
  /** The earliest day that can be picked. */
  minDate?: Date;
  /** The latest day that can be picked. */
  maxDate?: Date;
  /** The locale that formats the chosen dates in the field. */
  locale?: string;
};

export type SingleDatePickerProps = DatePickerBaseProps & {
  selectionMode?: "single";
  value?: Date;
  onValueChange?: (value: Date | undefined) => void;
  placeholder?: string;
};

export type RangeDatePickerProps = DatePickerBaseProps & {
  selectionMode: "range";
  value?: DateRange;
  onValueChange?: (value: DateRange | undefined) => void;
  startPlaceholder?: string;
  endPlaceholder?: string;
};

export type DatePickerProps = SingleDatePickerProps | RangeDatePickerProps;

// Serendie's calendar (src/components/DatePicker/styles.ts): days are circles, the chosen day
// fills with the primary container, the days inside a range sit on the selected surface and
// today carries an outline ring.
const calendarClassNames: Partial<ClassNames> = {
  root: "relative",
  month_caption: "flex h-control items-center px-2",
  caption_label: "type-label-large text-on-surface",
  nav: "absolute top-0 right-0 flex gap-1",
  button_previous: cn(
    "inline-flex size-control cursor-pointer items-center justify-center rounded-md text-on-surface [&_svg]:size-5",
    "not-aria-disabled:hover:bg-hovered-variant aria-disabled:cursor-not-allowed aria-disabled:text-on-disabled",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  ),
  button_next: cn(
    "inline-flex size-control cursor-pointer items-center justify-center rounded-md text-on-surface [&_svg]:size-5",
    "not-aria-disabled:hover:bg-hovered-variant aria-disabled:cursor-not-allowed aria-disabled:text-on-disabled",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  ),
  month_grid: "mt-1 border-collapse",
  weekday: "type-body-small size-control p-0 font-normal text-on-surface-variant",
  day: "p-0 text-center",
  day_button: cn(
    "type-body-small inline-flex size-control cursor-pointer items-center justify-center rounded-full tabular-nums text-on-surface",
    "enabled:hover:bg-hovered-variant disabled:cursor-not-allowed disabled:text-on-disabled",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  ),
  today: "[&>button]:border-2 [&>button]:border-outline",
  selected:
    "[&>button]:bg-primary-container [&>button]:text-on-primary-container [&>button]:enabled:hover:bg-primary-container",
  range_start: "rounded-l-full bg-selected-surface",
  range_end: "rounded-r-full bg-selected-surface",
  range_middle:
    "bg-selected-surface [&>button]:bg-transparent! [&>button]:text-on-surface! [&>button]:enabled:hover:bg-hovered-variant!",
};

function Chevron({ orientation }: { orientation?: "up" | "down" | "left" | "right" }) {
  return orientation === "left" ? <IconChevronLeft aria-hidden="true" /> : <IconChevronRight aria-hidden="true" />;
}

const calendarLabels = {
  labelPrevious: () => "Previous month",
  labelNext: () => "Next month",
};

function formatter(locale: string) {
  return new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", year: "numeric" });
}

function disabledDays(minDate: Date | undefined, maxDate: Date | undefined): Matcher[] {
  return [
    ...(minDate ? [{ before: minDate }] : []),
    ...(maxDate ? [{ after: maxDate }] : []),
  ];
}

// A range is picked as two clicks: the first starts a new range, the second ends it, whichever
// order the two days come in.
function extendRange(draft: DateRange | undefined, day: Date): { draft: DateRange; done: boolean } {
  if (draft === undefined) return { draft: { from: day }, done: false };
  return day < draft.from
    ? { draft: { from: day, to: draft.from }, done: true }
    : { draft: { from: draft.from, to: day }, done: true };
}

function Placeholder({ children }: { children: ReactNode }) {
  return <span className="text-on-surface-variant">{children}</span>;
}

export const DatePicker = forwardRef<HTMLButtonElement, DatePickerProps>((props, ref) => {
  const {
    label,
    description,
    invalid,
    invalidMessage,
    required,
    hideLabel,
    id,
    className,
    disabled = false,
    minDate,
    maxDate,
    locale = "en-US",
  } = props;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<DateRange | undefined>(undefined);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const valueId = useId();
  const format = formatter(locale);
  const isRange = props.selectionMode === "range";

  const start = isRange ? props.value?.from : props.value;
  const hasValue = start !== undefined;
  const valueText = !hasValue
    ? undefined
    : isRange
      ? `${format.format(props.value!.from)} – ${props.value!.to ? format.format(props.value!.to) : ""}`.trim()
      : format.format(props.value!);

  const changeOpen = (next: boolean) => {
    setOpen(next);
    setDraft(undefined);
  };

  const clear = () => {
    props.onValueChange?.(undefined);
    triggerRef.current?.focus();
  };

  const common = {
    autoFocus: true,
    defaultMonth: start ?? (maxDate && maxDate < new Date() ? maxDate : undefined),
    startMonth: minDate,
    endMonth: maxDate,
    disabled: disabledDays(minDate, maxDate),
    classNames: calendarClassNames,
    components: { Chevron },
    labels: calendarLabels,
  };

  const calendar =
    props.selectionMode === "range" ? (
      <DayPicker
        {...common}
        mode="range"
        selected={draft ?? props.value}
        onSelect={(_, day) => {
          const next = extendRange(draft, day);
          if (!next.done) {
            setDraft(next.draft);
            return;
          }
          props.onValueChange?.(next.draft);
          changeOpen(false);
        }}
      />
    ) : (
      <DayPicker
        {...common}
        mode="single"
        selected={props.value}
        onSelect={(_, day) => {
          props.onValueChange?.(day);
          changeOpen(false);
        }}
      />
    );

  return (
    <FieldFrame {...{ label, description, invalid, invalidMessage, required, hideLabel, id }}>
      {({ id: controlId, "aria-invalid": ariaInvalid, "aria-describedby": describedBy }) => (
        <PopoverPrimitive.Root open={open} onOpenChange={changeOpen}>
          <div className="relative">
            <PopoverPrimitive.Trigger
              ref={(node) => {
                triggerRef.current = node;
                if (typeof ref === "function") ref(node);
                else if (ref) ref.current = node;
              }}
              disabled={disabled}
              aria-describedby={[hasValue ? valueId : undefined, describedBy].filter(Boolean).join(" ") || undefined}
              className={cn(
                fieldControlStyle,
                "flex h-control cursor-pointer items-center gap-2 text-left",
                hasValue && !disabled && "pr-11",
                className,
              )}
              id={controlId}
              aria-invalid={ariaInvalid}
            >
              <IconCalendar aria-hidden="true" className="size-6 shrink-0" />
              <span aria-hidden="true" className="flex min-w-0 flex-1 items-center gap-2 truncate">
                {isRange ? (
                  <>
                    {props.value ? format.format(props.value.from) : <Placeholder>{props.startPlaceholder ?? "Start date"}</Placeholder>}
                    <IconArrowRight aria-hidden="true" className="size-5 shrink-0 text-on-surface-variant" />
                    {props.value?.to ? format.format(props.value.to) : <Placeholder>{props.endPlaceholder ?? "End date"}</Placeholder>}
                  </>
                ) : props.value ? (
                  format.format(props.value)
                ) : (
                  <Placeholder>{props.placeholder ?? "Select a date"}</Placeholder>
                )}
              </span>
              {hasValue && (
                <span id={valueId} className="sr-only">
                  {valueText}
                </span>
              )}
            </PopoverPrimitive.Trigger>
            {hasValue && !disabled && (
              <button
                type="button"
                aria-label="Clear dates"
                onClick={clear}
                className={cn(
                  "absolute top-0 right-0 inline-flex h-control w-11 cursor-pointer items-center justify-center rounded-md text-on-surface-variant",
                  "hover:bg-hovered-variant focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
                )}
              >
                <IconX aria-hidden="true" className="size-5" />
              </button>
            )}
          </div>
          <PopoverPrimitive.Portal>
            <PopoverPrimitive.Content
              align="start"
              sideOffset={4}
              collisionPadding={8}
              aria-label={isRange ? "Choose dates" : "Choose a date"}
              onOpenAutoFocus={(event) => event.preventDefault()}
              className="z-50 rounded-md border border-outline-dim bg-surface-container-bright p-2 text-on-surface shadow-lg"
            >
              {calendar}
            </PopoverPrimitive.Content>
          </PopoverPrimitive.Portal>
        </PopoverPrimitive.Root>
      )}
    </FieldFrame>
  );
});
DatePicker.displayName = "DatePicker";
