import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import { forwardRef, type ComponentProps, type MouseEvent } from "react";
import { cn } from "../../lib/cn";

const buttonStyle = cva(
  [
    "relative inline-flex items-center justify-center gap-1 overflow-hidden rounded-full",
    "cursor-pointer whitespace-nowrap disabled:cursor-not-allowed aria-busy:cursor-progress",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  ],
  {
    variants: {
      styleType: {
        filled: [
          "bg-primary-container text-on-primary-container",
          "enabled:hover:after:absolute enabled:hover:after:inset-0 enabled:hover:after:bg-hovered",
          "disabled:bg-disabled disabled:text-on-disabled",
        ],
        negative: [
          "bg-negative text-on-negative",
          "enabled:hover:after:absolute enabled:hover:after:inset-0 enabled:hover:after:bg-hovered",
          "disabled:bg-disabled disabled:text-on-disabled",
        ],
        outlined: [
          "border-2 border-outline-dim text-on-surface enabled:hover:bg-on-surface/5",
          "disabled:border-transparent disabled:bg-disabled disabled:text-on-disabled",
        ],
        ghost: [
          "text-primary enabled:hover:bg-on-surface/5 disabled:text-on-disabled",
        ],
      },
      size: {
        medium: "h-control px-6 type-label-large",
        small: "h-control-sm px-3 type-label-medium",
      },
    },
    defaultVariants: { styleType: "filled", size: "medium" },
  },
);

function Spinner() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-4 shrink-0 animate-spin motion-reduce:animate-none"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
    >
      <circle cx="12" cy="12" r="9" strokeOpacity="0.3" />
      <path d="M21 12a9 9 0 0 0-9-9" strokeLinecap="round" />
    </svg>
  );
}

export type ButtonProps = ComponentProps<"button"> &
  VariantProps<typeof buttonStyle> & {
    isLoading?: boolean;
    asChild?: boolean;
  };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { styleType, size, isLoading = false, asChild = false, className, children, onClick, ...rest },
    ref,
  ) => {
    const Comp = asChild ? Slot.Root : "button";

    function handleClick(event: MouseEvent<HTMLButtonElement>) {
      if (isLoading) {
        event.preventDefault();
        return;
      }
      onClick?.(event);
    }

    return (
      <Comp
        ref={ref}
        type={asChild ? undefined : "button"}
        className={cn(buttonStyle({ styleType, size }), className)}
        aria-busy={isLoading || undefined}
        onClick={handleClick}
        {...rest}
      >
        {asChild ? (
          children
        ) : (
          <>
            {isLoading && <Spinner />}
            {children}
          </>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";
