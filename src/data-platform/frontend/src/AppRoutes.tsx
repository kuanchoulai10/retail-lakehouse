import { TextLink } from "@retail-lakehouse/design-system";
import { Link, Navigate, Route, Routes } from "react-router";
import { discoveryPoliciesPath } from "./lib/discoveryPolicyPaths";
import { CatalogPage } from "./pages/CatalogPage";
import { CatalogsPage } from "./pages/CatalogsPage";
import { DiscoveryPoliciesPage } from "./pages/DiscoveryPoliciesPage";
import { DiscoveryPolicyPage } from "./pages/DiscoveryPolicyPage";
import { DiscoveryPolicyVersionPage } from "./pages/DiscoveryPolicyVersionPage";
import { GenericTablePage } from "./pages/GenericTablePage";
import { NamespacePage } from "./pages/NamespacePage";
import { PlatformSettingsPage } from "./pages/PlatformSettingsPage";
import { PoliciesPage } from "./pages/PoliciesPage";
import { PolicyVersionPage } from "./pages/PolicyVersionPage";
import { TableListPage } from "./pages/TableListPage";
import { TablePage } from "./pages/TablePage";
import { ViewPage } from "./pages/ViewPage";

function NotFound() {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p>
        <TextLink asChild>
          <Link to="/">
            Back to tables
          </Link>
        </TextLink>
      </p>
    </section>
  );
}

// The old /tables/:uuid route is gone with no redirect (spec); it lands on Page not found.
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<TableListPage />} />
      <Route path={discoveryPoliciesPath()} element={<DiscoveryPoliciesPage />} />
      <Route path={`${discoveryPoliciesPath()}/:name`} element={<DiscoveryPolicyPage />} />
      <Route path={`${discoveryPoliciesPath()}/:name/versions/:version`} element={<DiscoveryPolicyVersionPage />} />
      {/* The rules page became the discovery policies; old bookmarks land on the list. */}
      <Route path="/discovery-rules" element={<Navigate to={discoveryPoliciesPath()} replace />} />
      <Route path="/policies" element={<PoliciesPage />} />
      <Route path="/policies/:name/versions/:version" element={<PolicyVersionPage />} />
      <Route path="/platform-settings" element={<PlatformSettingsPage />} />
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
