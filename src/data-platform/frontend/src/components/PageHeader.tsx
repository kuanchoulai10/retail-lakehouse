import { TitleBar } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { ActionsMenu, type ActionItem } from "@/components/ActionsMenu";
import { Breadcrumbs, type Crumb } from "@/components/Breadcrumbs";

interface Props {
  title: string;
  breadcrumbs?: Crumb[];
  // Buttons beside the title, such as Run maintenance; on phones they move into the overflow
  // menu as `actionItems`.
  actions?: ReactNode;
  actionItems?: ActionItem[];
  // The object's Actions menu (Edit, Rename, Delete); on phones its items join the overflow menu.
  menuItems?: ActionItem[];
  // Facts below the title, such as status and counts.
  children?: ReactNode;
}

export function PageHeader({ title, breadcrumbs, actions, actionItems = [], menuItems = [], children }: Props) {
  const overflow = [...actionItems, ...menuItems];
  const hasActions = actions !== undefined || menuItems.length > 0;
  return (
    <header className="mb-4 flex flex-col gap-1">
      <TitleBar
        title={title}
        breadcrumbs={breadcrumbs === undefined ? undefined : <Breadcrumbs crumbs={breadcrumbs} />}
        actions={
          hasActions ? (
            <>
              {actions}
              {menuItems.length > 0 && <ActionsMenu items={menuItems} />}
            </>
          ) : undefined
        }
        overflowActions={overflow.length > 0 ? overflow : undefined}
      />
      {children !== undefined && (
        <div className="type-body-small flex flex-wrap items-center gap-x-4 gap-y-1 text-on-surface-variant">
          {children}
        </div>
      )}
    </header>
  );
}
