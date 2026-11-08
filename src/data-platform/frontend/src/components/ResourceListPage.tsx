import type { RowData } from "@tanstack/react-table";
import type { ActionItem } from "@/components/ActionsMenu";
import type { Crumb } from "@/components/Breadcrumbs";
import { PageHeader } from "@/components/PageHeader";
import { ResourceSection, type ResourceSectionProps } from "@/components/ResourceSection";
import type { ReactNode } from "react";

export type { ResourceColumn } from "@/components/ResourceSection";

interface Props<Row extends RowData> extends Omit<ResourceSectionProps<Row>, "title"> {
  title: string;
  breadcrumbs?: Crumb[];
  // Title of the list panel; the page title when left out.
  listTitle?: string;
  // The Actions menu of the object the page shows; on phones it joins the title bar's overflow menu.
  menuItems?: ActionItem[];
  // Content below the list, such as further lists or the object's properties.
  children?: ReactNode;
}

// The shape every catalog list page shares: header with breadcrumbs, then the list of
// children with its New button and per-row delete.
export function ResourceListPage<Row extends RowData>({
  title,
  breadcrumbs,
  listTitle,
  menuItems,
  children,
  ...section
}: Props<Row>) {
  return (
    <section>
      <PageHeader title={title} breadcrumbs={breadcrumbs} menuItems={menuItems} />
      <div className="flex flex-col gap-6">
        <ResourceSection title={listTitle ?? title} {...section} />
        {children}
      </div>
    </section>
  );
}
