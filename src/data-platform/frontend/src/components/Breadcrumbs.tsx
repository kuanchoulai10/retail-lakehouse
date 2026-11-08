import {
  Breadcrumbs as BreadcrumbTrail,
  type BreadcrumbsProps,
} from "@retail-lakehouse/design-system";
import { Link } from "react-router";

export interface Crumb {
  label: string;
  to?: string;
}

const renderLink: BreadcrumbsProps["renderLink"] = (item, children) => (
  <Link to={item.href ?? ""}>{children}</Link>
);

export function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <BreadcrumbTrail
      items={crumbs.map(({ label, to }) => ({ label, ...(to === undefined ? {} : { href: to }) }))}
      renderLink={renderLink}
    />
  );
}
