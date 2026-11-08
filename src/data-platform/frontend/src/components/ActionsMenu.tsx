import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  SerendieSymbolMoreHorizontal,
  type TitleBarOverflowAction,
} from "@retail-lakehouse/design-system";

// The same shape the title bar's phone overflow menu takes, so one list feeds both.
export type ActionItem = TitleBarOverflowAction;

export function ActionsMenu({ items }: { items: ActionItem[] }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" styleType="outlined">
          Actions
          <SerendieSymbolMoreHorizontal aria-hidden="true" className="size-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {items.map((item) => (
          <DropdownMenuItem
            key={item.label}
            onSelect={item.onSelect}
            disabled={item.disabled}
            className={item.destructive === true ? "text-negative-text" : undefined}
          >
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
