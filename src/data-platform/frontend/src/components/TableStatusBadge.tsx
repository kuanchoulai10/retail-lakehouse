import { CategoryBadge, type CategoryBadgeProps } from "@retail-lakehouse/design-system";

interface Props {
  status: string;
}

type Category = CategoryBadgeProps["category"];

// Which group a table is in (looked after, not looked after, not decided yet, gone), not how it is
// doing, so it takes the category badge, never the status colours.
function categoryOf(status: string): Category {
  switch (status) {
    case "managed":
      return "accent";
    case "dropped":
      return "muted";
    case "unmanaged":
    case "undecided":
    default:
      return "neutral";
  }
}

export function TableStatusBadge({ status }: Props) {
  const lower = status.toLowerCase();
  return <CategoryBadge category={categoryOf(lower)}>{lower.charAt(0).toUpperCase() + lower.slice(1)}</CategoryBadge>;
}
