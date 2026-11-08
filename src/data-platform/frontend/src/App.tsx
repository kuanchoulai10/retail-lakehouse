import { ThemeProvider, TooltipProvider } from "@retail-lakehouse/design-system";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { retryQuery } from "./api/retryQuery";
import { AppRoutes } from "./AppRoutes";
import { AppShell } from "./components/AppShell";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: retryQuery },
  },
});

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <BrowserRouter basename="/console">
            <AppShell>
              <AppRoutes />
            </AppShell>
          </BrowserRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
