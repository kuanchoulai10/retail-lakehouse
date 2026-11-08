import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  SerendieSymbolMoreHorizontal,
} from "@retail-lakehouse/design-system";

export interface ActionItem {
  label: string;
  onSelect: () => void;
}

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
          <DropdownMenuItem key={item.label} onSelect={item.onSelect}>
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
