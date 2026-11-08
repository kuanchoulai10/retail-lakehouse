import type { ReactNode } from "react";

export type TopAppBarProps = {
  title: ReactNode;
  headingIconButton?: ReactNode;
  trailingItems?: ReactNode;
};

export function TopAppBar({ title, headingIconButton, trailingItems }: TopAppBarProps) {
  return (
    <header className="sticky top-0 z-40 flex min-h-14 shrink-0 items-center gap-2 border-b border-outline bg-surface px-4 text-on-surface">
      {headingIconButton}
      <div className="type-title-large min-w-0 flex-1 truncate">{title}</div>
      {trailingItems && <div className="flex shrink-0 items-center gap-2">{trailingItems}</div>}
    </header>
  );
}
