import { getListCatalogsMockHandler, getGetCatalogMockHandler } from "@/api/generated/catalogs/catalogs.msw";
import { getGetPlatformSettingsMockHandler } from "@/api/generated/platform-settings/platform-settings.msw";
import { getListGenericTablesMockHandler } from "@/api/generated/generic-tables/generic-tables.msw";
import { getGetNamespaceMockHandler, getListNamespacesMockHandler } from "@/api/generated/namespaces/namespaces.msw";
import {
  getGetTableDiscoveryRulesMockHandler,
  getListCoveredCatalogsMockHandler,
  getReplaceTableDiscoveryRulesMockHandler,
} from "@/api/generated/discovery-rules/discovery-rules.msw";
import {
  getAttachTableMaintenancePolicyMockHandler,
  getCreateTableMaintenancePolicyMockHandler,
  getDeleteTableMaintenancePolicyMockHandler,
  getDetachTableMaintenancePolicyMockHandler,
  getGetApplicableMaintenancePolicyMockHandler,
  getGetTableApplicableMaintenancePolicyMockHandler,
  getGetTableMaintenancePolicyMockHandler,
  getGetTableMaintenancePolicyVersionMockHandler,
  getListTableMaintenancePoliciesMockHandler,
  getListTableMaintenancePolicyMappingsMockHandler,
  getUpdateTableMaintenancePolicyMockHandler,
} from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import {
  getGetCatalogTableMockHandler,
  getGetCatalogTablePartitionSpecComparisonMockHandler,
  getGetCatalogTableSchemaComparisonMockHandler,
  getGetTableCurrentMetricsMockHandler,
  getGetTableMetricTrendsMockHandler,
  getGetTableMockHandler,
  getListCatalogTablePartitionSpecVersionsMockHandler,
  getListCatalogTablePropertiesMockHandler,
  getListCatalogTableSchemaVersionsMockHandler,
  getListCatalogTablesMockHandler,
  getListTableCommitsMockHandler,
  getListTablesMockHandler,
  getResetCatalogTablePropertiesMockHandler,
  getSetTablePriorityMockHandler,
  getTriggerTableMaintenanceMockHandler,
} from "@/api/generated/tables/tables.msw";
import { getListTableMaintenanceRunsMockHandler } from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import { getListTableReconciliationsMockHandler } from "@/api/generated/table-reconciliations/table-reconciliations.msw";
import { getListViewsMockHandler } from "@/api/generated/views/views.msw";
import {
  applicablePolicy,
  CATALOGS,
  COMMITS,
  MAINTAINED_ORDERS,
  MAINTAINED_TABLES,
  NAMESPACES,
  ORDERS,
  ORDERS_CURRENT_METRICS,
  ORDERS_METRIC_TRENDS,
  ORDERS_PROPERTIES,
  ORDERS_SCHEMA_VERSIONS,
  ORDERS_SPEC_VERSIONS,
  ordersSchemaComparison,
  ordersSpecComparison,
  PLATFORM_SETTINGS,
  POLICIES,
  POLICY_MAPPINGS,
  RECONCILIATIONS,
  RETAIL,
  RETAIL_TABLES,
  RULES,
  RUNS,
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
    getListCatalogTablePropertiesMockHandler(ORDERS_PROPERTIES),
    getResetCatalogTablePropertiesMockHandler(ORDERS_PROPERTIES),
    getListCatalogTableSchemaVersionsMockHandler(ORDERS_SCHEMA_VERSIONS),
    getGetCatalogTableSchemaComparisonMockHandler(({ params, request }) => {
      const base = new URL(request.url).searchParams.get("base");
      return ordersSchemaComparison(Number(params.schemaId), base === null ? null : Number(base));
    }),
    getListCatalogTablePartitionSpecVersionsMockHandler(ORDERS_SPEC_VERSIONS),
    getGetCatalogTablePartitionSpecComparisonMockHandler(({ params }) => ordersSpecComparison(Number(params.specId))),
    getListCoveredCatalogsMockHandler({ catalogs: ["iceberg"] }),
    getListTablesMockHandler(MAINTAINED_TABLES),
    getGetTableMockHandler(MAINTAINED_ORDERS),
    getSetTablePriorityMockHandler(async ({ request }) => ({
      ...MAINTAINED_ORDERS,
      priority: ((await request.json()) as { priority: string }).priority,
    })),
    getTriggerTableMaintenanceMockHandler({ accepted: true }),
    getGetTableCurrentMetricsMockHandler(ORDERS_CURRENT_METRICS),
    getGetTableMetricTrendsMockHandler(({ request }) => {
      const hours = Number((new URL(request.url).searchParams.get("range") ?? "6h").replace("h", ""));
      const start = Date.parse(ORDERS_METRIC_TRENDS.end) - hours * 3_600_000;
      return {
        ...ORDERS_METRIC_TRENDS,
        time_range: `${hours}h`,
        start: new Date(start).toISOString(),
        points: ORDERS_METRIC_TRENDS.points.filter((point) => Date.parse(point.at) >= start),
      };
    }),
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
    getGetPlatformSettingsMockHandler(PLATFORM_SETTINGS),
    getListTableReconciliationsMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      const before = query.get("before");
      const limit = Number(query.get("limit") ?? 50);
      return RECONCILIATIONS.filter(
        (r) => before === null || Date.parse(r.reconciled_at) < Date.parse(before),
      ).slice(0, limit);
    }),
    getGetTableDiscoveryRulesMockHandler({ version: 1, rules: RULES }),
    getReplaceTableDiscoveryRulesMockHandler({ version: 2, rules: RULES }),
    getListTableMaintenancePoliciesMockHandler({ policies: POLICIES }),
    getListTableMaintenancePolicyMappingsMockHandler(({ params }) => ({
      mappings: POLICY_MAPPINGS.filter((mapping) => mapping.policy_name === params.name),
    })),
    getGetTableMaintenancePolicyMockHandler(({ params }) => POLICIES.find((p) => p.name === params.name) ?? POLICIES[0]!),
    getCreateTableMaintenancePolicyMockHandler(async ({ request }) => ({
      ...POLICIES[0]!,
      ...((await request.json()) as object),
      version: 1,
    })),
    getUpdateTableMaintenancePolicyMockHandler(({ params }) => {
      const current = POLICIES.find((p) => p.name === params.name) ?? POLICIES[0]!;
      return { ...current, version: current.version + 1 };
    }),
    getDeleteTableMaintenancePolicyMockHandler(),
    getGetTableMaintenancePolicyVersionMockHandler(({ params }) => {
      const policy = POLICIES.find((p) => p.name === params.name) ?? POLICIES[0]!;
      return { ...policy, version: Number(params.version) };
    }),
    getGetApplicableMaintenancePolicyMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      return applicablePolicy(query.get("catalog") ?? "", query.get("namespace")?.split(".") ?? []);
    }),
    getGetTableApplicableMaintenancePolicyMockHandler(applicablePolicy(ORDERS.catalog, ORDERS.namespace)),
    getAttachTableMaintenancePolicyMockHandler(async ({ params, request }) => ({
      policy_id: (POLICIES.find((p) => p.name === params.name) ?? POLICIES[0]!).id,
      policy_name: params.name,
      target: { ...((await request.json()).target), table_uuid: null },
      attached_at: "2026-11-12T09:00:00Z",
    })),
    getDetachTableMaintenancePolicyMockHandler(),
  ];
}
