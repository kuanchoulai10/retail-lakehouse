import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Link, Route, Routes } from "react-router";
import { retryQuery } from "./api/retryQuery";
import { TableListPage } from "./pages/TableListPage";
import { TablePage } from "./pages/TablePage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: retryQuery },
  },
});

function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Back to tables</Link>
      </p>
    </section>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/console">
        <header className="topbar">
          <Link to="/" className="brand">
            Data Platform Console
          </Link>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<TableListPage />} />
            <Route path="/tables/:uuid/:tab?" element={<TablePage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
