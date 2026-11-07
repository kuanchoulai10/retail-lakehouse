import type { ReactNode } from "react";
import type { Crumb } from "@/components/Breadcrumbs";
import { PageHeader } from "@/components/PageHeader";
import { ResourceSection, type ResourceSectionProps } from "@/components/ResourceSection";

export type { ResourceColumn } from "@/components/ResourceSection";

interface Props<Row> extends Omit<ResourceSectionProps<Row>, "title"> {
  title: string;
  breadcrumbs?: Crumb[];
  // Title of the list panel; the page title when left out.
  listTitle?: string;
  // Page actions beside the title, such as the Actions menu of the object the page shows.
  actions?: ReactNode;
  // Content below the list, such as further lists or the object's properties.
  children?: ReactNode;
}

// The shape every catalog list page shares: header with breadcrumbs, then the list of
// children with its New button and per-row delete.
export function ResourceListPage<Row>({
  title,
  breadcrumbs,
  listTitle,
  actions,
  children,
  ...section
}: Props<Row>) {
  return (
    <section>
      <PageHeader title={title} breadcrumbs={breadcrumbs} actions={actions} />
      <div className="flex flex-col gap-6">
        <ResourceSection title={listTitle ?? title} {...section} />
        {children}
      </div>
    </section>
  );
}
