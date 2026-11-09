import type { IconProps, TablerIcon } from "@tabler/icons-react";
import { forwardRef } from "react";

// Tabler draws a 2px line, heavier than Serendie's symbols; every icon defaults to 1.5,
// and a caller can still pass its own stroke.
export const DEFAULT_ICON_STROKE = 1.5;

export function withDefaultStroke(Icon: TablerIcon): TablerIcon {
  const Wrapped = forwardRef<SVGSVGElement, IconProps>(({ stroke = DEFAULT_ICON_STROKE, ...props }, ref) => (
    <Icon ref={ref} stroke={stroke} {...props} />
  ));
  Wrapped.displayName = Icon.displayName;
  return Wrapped;
}
