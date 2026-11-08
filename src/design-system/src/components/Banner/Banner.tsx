import { cva } from "class-variance-authority";
import { forwardRef, type ComponentProps, type ReactNode } from "react";
import {
  SerendieSymbolAlertCircle,
  SerendieSymbolAlertTriangle,
  SerendieSymbolCheckCircle,
  SerendieSymbolInformation,
  type IconComponent,
} from "../../icons";
import { cn } from "../../lib/cn";

type BannerType = "information" | "notice" | "negative" | "positive";

const bannerStyle = cva("flex items-start gap-3 rounded-md p-3", {
  variants: {
    type: {
      information: "bg-primary-container text-on-primary-container",
      notice: "bg-notice-container text-on-notice-container",
      negative: "bg-negative-container text-on-negative-container",
      positive: "bg-positive-container text-on-positive-container",
    },
  },
});

const icons: Record<BannerType, IconComponent> = {
  information: SerendieSymbolInformation,
  notice: SerendieSymbolAlertTriangle,
  negative: SerendieSymbolAlertCircle,
  positive: SerendieSymbolCheckCircle,
};

export type BannerProps = Omit<ComponentProps<"div">, "title"> & {
  type: BannerType;
  title: ReactNode;
};

export const Banner = forwardRef<HTMLDivElement, BannerProps>(
  ({ type, title, className, children, ...rest }, ref) => {
    const Icon = icons[type];
    return (
      <div
        ref={ref}
        role={type === "negative" ? "alert" : "status"}
        className={cn(bannerStyle({ type }), className)}
        {...rest}
      >
        <Icon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div className="min-w-0">
          <p className="type-title-small">{title}</p>
          <div className="type-body-medium">{children}</div>
        </div>
      </div>
    );
  },
);
Banner.displayName = "Banner";
