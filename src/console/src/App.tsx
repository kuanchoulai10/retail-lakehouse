import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Link, Route, Routes, useParams } from "react-router";
import { TableListPage } from "./pages/TableListPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

function TablePagePlaceholder() {
  const { uuid } = useParams();
  return (
    <section>
      <h1>Table</h1>
      <p>Table {uuid} — the table page arrives in a later release.</p>
    </section>
  );
}

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
            <Route path="/tables/:uuid/:tab?" element={<TablePagePlaceholder />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
