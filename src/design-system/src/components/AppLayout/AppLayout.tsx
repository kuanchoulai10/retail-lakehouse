import { Slot } from "radix-ui";
import { useRef, useState, type ReactElement, type ReactNode } from "react";
import { SerendieSymbolMenu } from "../../icons";
import { Drawer } from "../Drawer/Drawer";
import { IconButton } from "../IconButton/IconButton";
import { SideNavigation, type SideNavigationProps } from "../SideNavigation/SideNavigation";
import { TopAppBar } from "../TopAppBar/TopAppBar";

export type AppLayoutProps = {
  productName: string;
  navigation: SideNavigationProps;
  trailingItems?: ReactNode;
  renderProductLink?: (children: ReactNode) => ReactElement;
  children: ReactNode;
};

export function AppLayout({
  productName,
  navigation,
  trailingItems,
  renderProductLink,
  children,
}: AppLayoutProps) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const main = useRef<HTMLElement>(null);
  const navigated = useRef(false);

  const handleNavigate = () => {
    navigated.current = true;
    setIsDrawerOpen(false);
    navigation.onNavigate?.();
  };

  const handleCloseAutoFocus = (event: Event) => {
    if (navigated.current) {
      navigated.current = false;
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
          <IconButton
            aria-label="Open navigation menu"
            styleType="ghost"
            icon={<SerendieSymbolMenu />}
            className="md:hidden"
            onClick={() => setIsDrawerOpen(true)}
          />
        }
        trailingItems={trailingItems}
      />
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-56 shrink-0 overflow-y-auto border-r border-outline md:block">
          <SideNavigation {...navigation} />
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
