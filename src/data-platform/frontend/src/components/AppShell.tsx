import {
  AppLayout,
  IconBook,
  IconTable,
  IconRadar,
  IconAdjustmentsHorizontal,
  ThemePicker,
  type SideNavigationItem,
  type SideNavigationProps,
} from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { catalogsPath } from "@/lib/catalogPaths";

const PRODUCT_NAME = "Lakehouse";

interface NavEntry {
  href: string;
  label: string;
  icon: SideNavigationItem["icon"];
  matches: (pathname: string) => boolean;
}

const NAV_ENTRIES: NavEntry[] = [
  {
    href: "/",
    label: "Tables",
    icon: IconTable,
    matches: (pathname) => pathname === "/",
  },
  {
    href: catalogsPath(),
    label: "Catalog",
    icon: IconBook,
    matches: (pathname) => pathname.startsWith(catalogsPath()),
  },
  {
    href: "/presets",
    label: "Presets",
    icon: IconAdjustmentsHorizontal,
    matches: (pathname) => pathname.startsWith("/presets"),
  },
  {
    href: "/discovery-rules",
    label: "Discovery rules",
    icon: IconRadar,
    matches: (pathname) => pathname.startsWith("/discovery-rules"),
  },
];

const renderLink: SideNavigationProps["renderLink"] = (item, children) => (
  <Link to={item.href}>{children}</Link>
);

const renderProductLink = (children: ReactNode) => <Link to="/">{children}</Link>;

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const navigation: SideNavigationProps = {
    items: NAV_ENTRIES.map(({ href, label, icon, matches }) => ({
      href,
      label,
      icon,
      isActive: matches(pathname),
    })),
    renderLink,
  };

  return (
    <AppLayout
      productName={PRODUCT_NAME}
      navigation={navigation}
      renderProductLink={renderProductLink}
      trailingItems={<ThemePicker />}
    >
      <div className="max-w-[1200px]">{children}</div>
    </AppLayout>
  );
}
