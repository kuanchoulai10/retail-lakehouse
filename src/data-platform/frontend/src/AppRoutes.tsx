import { Link, Route, Routes } from "react-router";
import { CatalogPage } from "./pages/CatalogPage";
import { CatalogsPage } from "./pages/CatalogsPage";
import { DiscoveryRulesPage } from "./pages/DiscoveryRulesPage";
import { GenericTablePage } from "./pages/GenericTablePage";
import { NamespacePage } from "./pages/NamespacePage";
import { PresetsPage } from "./pages/PresetsPage";
import { TableListPage } from "./pages/TableListPage";
import { TablePage } from "./pages/TablePage";
import { ViewPage } from "./pages/ViewPage";

function NotFound() {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p>
        <Link to="/" className="text-on-surface-variant underline-offset-4 hover:text-on-surface hover:underline">
          Back to tables
        </Link>
      </p>
    </section>
  );
}

// The old /tables/:uuid route is gone with no redirect (spec); it lands on Page not found.
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<TableListPage />} />
      <Route path="/presets" element={<PresetsPage />} />
      <Route path="/discovery-rules" element={<DiscoveryRulesPage />} />
      <Route path="/catalogs" element={<CatalogsPage />} />
      <Route path="/catalogs/:catalog" element={<CatalogPage />} />
      <Route path="/catalogs/:catalog/namespaces/:namespace" element={<NamespacePage />} />
      <Route path="/catalogs/:catalog/namespaces/:namespace/tables/:table/:tab?" element={<TablePage />} />
      <Route path="/catalogs/:catalog/namespaces/:namespace/views/:view" element={<ViewPage />} />
      <Route path="/catalogs/:catalog/namespaces/:namespace/generic-tables/:name" element={<GenericTablePage />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
