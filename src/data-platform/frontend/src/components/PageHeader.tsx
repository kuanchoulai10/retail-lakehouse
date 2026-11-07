import type { ReactNode } from "react";

interface Props {
  title: string;
  breadcrumb?: string;
  actions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, breadcrumb, actions, children }: Props) {
  return (
    <header className="mb-6 flex flex-col gap-2">
      {breadcrumb !== undefined && (
        <p className="text-[13px] text-muted-foreground">{breadcrumb}</p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight break-words min-w-0">{title}</h1>
        {actions !== undefined && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children !== undefined && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-muted-foreground">
          {children}
        </div>
      )}
    </header>
  );
}
