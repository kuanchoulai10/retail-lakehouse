import { ThemeProvider, TooltipProvider } from "@retail-lakehouse/design-system";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { AppRoutes } from "@/AppRoutes";
import { AppShell } from "@/components/AppShell";

// The whole console at one URL, as App renders it, for page stories. Each mount gets its own
// query cache, and failed requests are not retried, so error stories settle at once.
export function ConsolePage({ route }: { route: string }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false, staleTime: Infinity, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <MemoryRouter initialEntries={[route]}>
            <AppShell>
              <AppRoutes />
            </AppShell>
          </MemoryRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
