import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Link, Route, Routes } from "react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import { retryQuery } from "./api/retryQuery";
import { AppShell } from "./components/AppShell";
import { DiscoveryRulesPage } from "./pages/DiscoveryRulesPage";
import { PresetsPage } from "./pages/PresetsPage";
import { TableListPage } from "./pages/TableListPage";
import { TablePage } from "./pages/TablePage";
import { ThemeProvider } from "./theme/ThemeProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: retryQuery },
  },
});

function NotFound() {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p>
        <Link to="/" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
          Back to tables
        </Link>
      </p>
    </section>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <BrowserRouter basename="/console">
            <AppShell>
              <Routes>
                <Route path="/" element={<TableListPage />} />
                <Route path="/tables/:uuid/:tab?" element={<TablePage />} />
                <Route path="/presets" element={<PresetsPage />} />
                <Route path="/discovery-rules" element={<DiscoveryRulesPage />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </AppShell>
          </BrowserRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
