import type { ReactNode } from "react";
import { Breadcrumbs, type Crumb } from "@/components/Breadcrumbs";

interface Props {
  title: string;
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, breadcrumbs, actions, children }: Props) {
  return (
    <header className="mb-6 flex flex-col gap-2">
      {breadcrumbs !== undefined && <Breadcrumbs crumbs={breadcrumbs} />}
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
