import { Menu, Table2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { ThemeSwitch } from "./ThemeSwitch";

const PRODUCT_NAME = "Lakehouse";

function isTablesPath(pathname: string): boolean {
  return pathname === "/" || pathname.startsWith("/tables/");
}

function Brand({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link
      to="/"
      onClick={onNavigate}
      className="text-sm font-semibold tracking-tight text-foreground hover:no-underline"
    >
      {PRODUCT_NAME}
    </Link>
  );
}

function MainNav({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const active = isTablesPath(pathname);
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      <Link
        to="/"
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex h-8 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground",
          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground hover:no-underline",
          active && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
        )}
      >
        <Table2 aria-hidden="true" className="size-4" />
        Tables
      </Link>
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="flex min-h-svh bg-background font-sans text-sm text-foreground">
      <aside className="sticky top-0 hidden h-svh w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex">
        <div className="flex h-14 items-center px-4">
          <Brand />
        </div>
        <div className="flex-1 px-2">
          <MainNav />
        </div>
        <div className="border-t border-sidebar-border p-2">
          <ThemeSwitch />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-sidebar-border bg-sidebar px-4 md:hidden">
          <Brand />
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Open menu">
                <Menu aria-hidden="true" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              aria-describedby={undefined}
              className="w-64 gap-0 bg-sidebar p-0 text-sidebar-foreground"
            >
              <div className="flex h-14 items-center px-4">
                <SheetTitle className="sr-only">Menu</SheetTitle>
                <Brand onNavigate={closeMenu} />
              </div>
              <div className="flex-1 px-2">
                <MainNav onNavigate={closeMenu} />
              </div>
              <div className="border-t border-sidebar-border p-2">
                <ThemeSwitch />
              </div>
            </SheetContent>
          </Sheet>
        </header>
        <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="max-w-[1200px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
