import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

const iconButtonStyle = cva(
  [
    "relative inline-flex size-touch shrink-0 items-center justify-center overflow-hidden",
    "cursor-pointer disabled:cursor-not-allowed [&_svg]:size-6",
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
        outlined: [
          "border-2 border-outline-dim text-on-surface enabled:hover:bg-hovered-variant",
          "disabled:border-transparent disabled:bg-disabled disabled:text-on-disabled",
        ],
        ghost: "text-on-surface enabled:hover:bg-hovered-variant disabled:text-on-disabled",
      },
      shape: {
        circle: "rounded-full",
        rectangle: "rounded-md",
      },
    },
    defaultVariants: { styleType: "filled", shape: "circle" },
  },
);

export type IconButtonProps = Omit<ComponentProps<"button">, "aria-label" | "children"> &
  VariantProps<typeof iconButtonStyle> & {
    icon: ReactNode;
    "aria-label": string;
  };

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, styleType, shape, className, ...rest }, ref) => (
    <button
      ref={ref}
      type="button"
      className={cn(iconButtonStyle({ styleType, shape }), className)}
      {...rest}
    >
      {icon}
    </button>
  ),
);
IconButton.displayName = "IconButton";
