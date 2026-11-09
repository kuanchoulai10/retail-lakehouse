import { getListCatalogsMockHandler, getGetCatalogMockHandler } from "@/api/generated/catalogs/catalogs.msw";
import { getListGenericTablesMockHandler } from "@/api/generated/generic-tables/generic-tables.msw";
import { getGetNamespaceMockHandler, getListNamespacesMockHandler } from "@/api/generated/namespaces/namespaces.msw";
import {
  getGetTableDiscoverySettingsMockHandler,
  getListCoveredCatalogsMockHandler,
} from "@/api/generated/table-discovery-settings/table-discovery-settings.msw";
import { getListTableDiscoveryRulesMockHandler } from "@/api/generated/table-discovery-rules/table-discovery-rules.msw";
import { getListTableMaintenancePresetsMockHandler } from "@/api/generated/table-maintenance-presets/table-maintenance-presets.msw";
import {
  getGetCatalogTableMockHandler,
  getGetTableHealthMockHandler,
  getGetTableMockHandler,
  getGetTableStorageMockHandler,
  getListCatalogTablesMockHandler,
  getListTableCommitsMockHandler,
  getListTablesMockHandler,
} from "@/api/generated/tables/tables.msw";
import { getListTableMaintenanceRunsMockHandler } from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import { getListTableReconciliationsMockHandler } from "@/api/generated/table-reconciliations/table-reconciliations.msw";
import { getListViewsMockHandler } from "@/api/generated/views/views.msw";
import {
  CATALOGS,
  COMMITS,
  HEALTH,
  MAINTAINED_ORDERS,
  MAINTAINED_TABLES,
  NAMESPACES,
  ORDERS,
  PRESETS,
  RECONCILIATIONS,
  RETAIL,
  RETAIL_TABLES,
  RULES,
  RUNS,
  STORAGE,
} from "./storyData";

// Every read the console makes, answered from storyData through the generated MSW handlers.
// A story puts its own handlers in front of these to show an empty list, an error or a wait.
export function lakehouseHandlers() {
  return [
    getListCatalogsMockHandler(CATALOGS),
    getGetCatalogMockHandler(({ params }) => CATALOGS.find((c) => c.name === params.catalog) ?? CATALOGS[0]!),
    getListNamespacesMockHandler(({ request }) =>
      new URL(request.url).searchParams.has("parent") ? [] : NAMESPACES,
    ),
    getGetNamespaceMockHandler(RETAIL),
    getListCatalogTablesMockHandler(RETAIL_TABLES),
    getListViewsMockHandler([{ catalog: "iceberg", namespace: ["retail"], name: "daily_revenue" }]),
    getListGenericTablesMockHandler([]),
    getGetCatalogTableMockHandler(ORDERS),
    getListCoveredCatalogsMockHandler({ catalogs: ["iceberg"] }),
    getListTablesMockHandler(MAINTAINED_TABLES),
    getGetTableMockHandler(MAINTAINED_ORDERS),
    getGetTableHealthMockHandler(HEALTH),
    getGetTableStorageMockHandler(STORAGE),
    getListTableCommitsMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      const since = query.get("since");
      const before = query.get("before");
      const writer = query.get("writer");
      return {
        ...COMMITS,
        items: COMMITS.items.filter(
          (commit) =>
            (since === null || Date.parse(commit.committed_at) >= Date.parse(since)) &&
            (before === null || Date.parse(commit.committed_at) < Date.parse(before)) &&
            (writer === null || commit.writer === writer),
        ),
      };
    }),
    getListTableMaintenanceRunsMockHandler(RUNS),
    getListTableReconciliationsMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      const before = query.get("before");
      const limit = Number(query.get("limit") ?? 50);
      return RECONCILIATIONS.filter(
        (r) => before === null || Date.parse(r.reconciled_at) < Date.parse(before),
      ).slice(0, limit);
    }),
    getListTableMaintenancePresetsMockHandler(PRESETS),
    getListTableDiscoveryRulesMockHandler(RULES),
    getGetTableDiscoverySettingsMockHandler({ enabled: true, updated_at: "2026-11-01T09:00:00Z" }),
  ];
}
