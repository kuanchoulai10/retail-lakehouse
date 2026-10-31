import type { ReactNode } from "react";

interface Props {
  title: string;
  actions?: ReactNode;
  children?: ReactNode;
}

export function Panel({ title, actions, children }: Props) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-background">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-2.5">
        <h2 className="text-sm font-medium">{title}</h2>
        {actions !== undefined && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div>{children}</div>
    </section>
  );
}
