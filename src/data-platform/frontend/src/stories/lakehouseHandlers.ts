import { getListCatalogsMockHandler, getGetCatalogMockHandler } from "@/api/generated/catalogs/catalogs.msw";
import { getListCompactionCandidatesMockHandler } from "@/api/generated/compaction-candidates/compaction-candidates.msw";
import {
  getGetCompactionRoundMockHandler,
  getGetSchedulerSettingsMockHandler,
  getListCompactionRoundsMockHandler,
} from "@/api/generated/compaction-rounds/compaction-rounds.msw";
import { getListGenericTablesMockHandler } from "@/api/generated/generic-tables/generic-tables.msw";
import { getGetNamespaceMockHandler, getListNamespacesMockHandler } from "@/api/generated/namespaces/namespaces.msw";
import {
  getGetTableDiscoveryRulesMockHandler,
  getListCoveredCatalogsMockHandler,
  getPreviewTableDiscoveryRulesMockHandler,
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
  applicablePolicy,
  CANDIDATES,
  CATALOGS,
  COMMITS,
  HEALTH,
  MAINTAINED_ORDERS,
  MAINTAINED_TABLES,
  NAMESPACES,
  ORDERS,
  POLICIES,
  POLICY_MAPPINGS,
  RECONCILIATIONS,
  RETAIL,
  RETAIL_TABLES,
  ROUNDS,
  RULES,
  RULES_PREVIEW,
  RUNS,
  SCHEDULER_SETTINGS,
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
    getListCompactionCandidatesMockHandler(CANDIDATES),
    getListCompactionRoundsMockHandler(ROUNDS),
    getGetSchedulerSettingsMockHandler(SCHEDULER_SETTINGS),
    getGetCompactionRoundMockHandler(({ params }) => ROUNDS.find((r) => r.round_id === params.roundId) ?? ROUNDS[0]!),
    getListTableReconciliationsMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      const before = query.get("before");
      const limit = Number(query.get("limit") ?? 50);
      return RECONCILIATIONS.filter(
        (r) => before === null || Date.parse(r.reconciled_at) < Date.parse(before),
      ).slice(0, limit);
    }),
    getGetTableDiscoveryRulesMockHandler({ version: 1, rules: RULES }),
    getPreviewTableDiscoveryRulesMockHandler(RULES_PREVIEW),
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
      policy_name: params.name,
      target: { ...((await request.json()).target), table_uuid: null },
      attached_at: "2026-11-12T09:00:00Z",
    })),
    getDetachTableMaintenancePolicyMockHandler(),
  ];
}
