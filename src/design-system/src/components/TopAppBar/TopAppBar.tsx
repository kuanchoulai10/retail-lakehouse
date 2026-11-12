import type { ReactNode } from "react";

export type TopAppBarProps = {
  title: ReactNode;
  headingIconButton?: ReactNode;
  leadingItems?: ReactNode;
  trailingItems?: ReactNode;
};

export function TopAppBar({ title, headingIconButton, leadingItems, trailingItems }: TopAppBarProps) {
  return (
    <header className="sticky top-0 z-40 flex min-h-14 shrink-0 items-center gap-2 border-b border-outline bg-surface px-4 text-on-surface">
      {headingIconButton}
      <div className="type-title-large min-w-0 truncate">{title}</div>
      {leadingItems && <div className="flex shrink-0 items-center gap-2">{leadingItems}</div>}
      <div className="flex-1" />
      {trailingItems && <div className="flex shrink-0 items-center gap-2">{trailingItems}</div>}
    </header>
  );
}
