import { Slot } from "radix-ui";
import { useEffect, useId, useRef, useState, type ReactElement, type ReactNode } from "react";
import { IconLayoutSidebarLeftCollapse, IconLayoutSidebarLeftExpand, IconMenu2 } from "../../icons";
import { cn } from "../../lib/cn";
import { Drawer } from "../Drawer/Drawer";
import { IconButton } from "../IconButton/IconButton";
import { SideNavigation, type SideNavigationProps } from "../SideNavigation/SideNavigation";
import { TopAppBar } from "../TopAppBar/TopAppBar";

// The expanded window class starts at 768px (--sd-system-dimension-breakpoint-expanded).
const EXPANDED_WINDOW = "(min-width: 48rem)";
const SIDEBAR_STORAGE_KEY = "ds-app-layout-sidebar-collapsed";

// The collapsed choice is a per-browser convenience: storage can be missing or refuse access.
function readSidebarCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeSidebarCollapsed(isCollapsed: boolean) {
  try {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed));
  } catch {
    // Not remembered; the sidebar still toggles.
  }
}

export type AppLayoutProps = {
  productName: string;
  navigation: SideNavigationProps;
  leadingItems?: ReactNode;
  trailingItems?: ReactNode;
  renderProductLink?: (children: ReactNode) => ReactElement;
  children: ReactNode;
};

export function AppLayout({
  productName,
  navigation,
  leadingItems,
  trailingItems,
  renderProductLink,
  children,
}: AppLayoutProps) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(readSidebarCollapsed);
  const sidebarId = useId();
  const main = useRef<HTMLElement>(null);
  const focusMainOnClose = useRef(false);

  // The drawer only exists below 768px; crossing to the expanded window closes it and, as its
  // menu button is hidden there, moves focus to the main region instead.
  useEffect(() => {
    if (!isDrawerOpen) return;
    const expanded = window.matchMedia(EXPANDED_WINDOW);
    const closeWhenExpanded = () => {
      if (expanded.matches) {
        focusMainOnClose.current = true;
        setIsDrawerOpen(false);
      }
    };
    closeWhenExpanded();
    expanded.addEventListener("change", closeWhenExpanded);
    return () => expanded.removeEventListener("change", closeWhenExpanded);
  }, [isDrawerOpen]);

  const handleNavigate = () => {
    focusMainOnClose.current = true;
    setIsDrawerOpen(false);
    navigation.onNavigate?.();
  };

  const toggleSidebar = () => {
    const next = !isSidebarCollapsed;
    setIsSidebarCollapsed(next);
    writeSidebarCollapsed(next);
  };

  const handleCloseAutoFocus = (event: Event) => {
    if (focusMainOnClose.current) {
      focusMainOnClose.current = false;
      event.preventDefault();
      main.current?.focus();
    }
  };

  return (
    <div className="flex h-dvh flex-col bg-surface text-on-surface">
      <TopAppBar
        title={
          renderProductLink ? (
            <Slot.Root className="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring">
              {renderProductLink(productName)}
            </Slot.Root>
          ) : (
            productName
          )
        }
        headingIconButton={
          <>
            <IconButton
              aria-label="Open navigation menu"
              styleType="ghost"
              icon={<IconMenu2 />}
              className="md:hidden"
              onClick={() => setIsDrawerOpen(true)}
            />
            <IconButton
              aria-label={isSidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
              aria-expanded={!isSidebarCollapsed}
              aria-controls={sidebarId}
              styleType="ghost"
              icon={isSidebarCollapsed ? <IconLayoutSidebarLeftExpand /> : <IconLayoutSidebarLeftCollapse />}
              className="hidden md:inline-flex"
              onClick={toggleSidebar}
            />
          </>
        }
        leadingItems={leadingItems}
        trailingItems={trailingItems}
      />
      <div className="flex min-h-0 flex-1">
        <aside
          id={sidebarId}
          className={cn(
            "hidden shrink-0 overflow-x-hidden overflow-y-auto border-r border-outline md:block",
            "transition-[width] duration-150 motion-reduce:transition-none",
            isSidebarCollapsed ? "w-14" : "w-56",
          )}
        >
          <SideNavigation {...navigation} isCollapsed={isSidebarCollapsed} />
        </aside>
        <main ref={main} tabIndex={-1} className="min-w-0 flex-1 overflow-y-auto p-4 outline-none md:p-6">
          {children}
        </main>
      </div>
      <Drawer
        side="left"
        title={productName}
        isOpen={isDrawerOpen}
        onOpenChange={setIsDrawerOpen}
        onCloseAutoFocus={handleCloseAutoFocus}
      >
        <SideNavigation {...navigation} onNavigate={handleNavigate} />
      </Drawer>
    </div>
  );
}
