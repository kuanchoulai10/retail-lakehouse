import { HttpResponse } from "msw";
import { getListCatalogsMockHandler, getGetCatalogMockHandler } from "@/api/generated/catalogs/catalogs.msw";
import { getGetPlatformSettingsMockHandler } from "@/api/generated/platform-settings/platform-settings.msw";
import { getListGenericTablesMockHandler } from "@/api/generated/generic-tables/generic-tables.msw";
import { getGetNamespaceMockHandler, getListNamespacesMockHandler } from "@/api/generated/namespaces/namespaces.msw";
import {
  getAttachTableDiscoveryPolicyMockHandler,
  getCreateTableDiscoveryPolicyMockHandler,
  getDeleteTableDiscoveryPolicyMockHandler,
  getDetachTableDiscoveryPolicyMockHandler,
  getGetTableDiscoveryPolicyMockHandler,
  getGetTableDiscoveryPolicyVersionMockHandler,
  getListScannedCatalogsMockHandler,
  getListTableDiscoveryPoliciesMockHandler,
  getListTableDiscoveryPolicyAttachmentsMockHandler,
  getUpdateTableDiscoveryPolicyMockHandler,
} from "@/api/generated/discovery-policies/discovery-policies.msw";
import {
  getAttachTableMaintenancePolicyMockHandler,
  getCreateTableMaintenancePolicyMockHandler,
  getDeleteTableMaintenancePolicyMockHandler,
  getDetachTableMaintenancePolicyMockHandler,
  getGetTableMaintenancePolicyMockHandler,
  getGetTableMaintenancePolicyVersionMockHandler,
  getListTableMaintenancePoliciesMockHandler,
  getListTableMaintenancePolicyAttachmentsMockHandler,
  getUpdateTableMaintenancePolicyMockHandler,
} from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import {
  getGetCatalogTableMockHandler,
  getGetCatalogTablePartitionSpecComparisonMockHandler,
  getGetCatalogTableSchemaComparisonMockHandler,
  getGetEffectivePoliciesMockHandler,
  getGetTableCurrentMetricsMockHandler,
  getGetTableEffectivePoliciesMockHandler,
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
import {
  getGetTableMaintenanceRunMockHandler,
  getListTableMaintenanceRunsMockHandler,
} from "@/api/generated/table-maintenance-runs/table-maintenance-runs.msw";
import {
  getGetTableReconciliationMockHandler,
  getListTableReconciliationsMockHandler,
} from "@/api/generated/table-reconciliations/table-reconciliations.msw";
import { getListViewsMockHandler } from "@/api/generated/views/views.msw";
import {
  CANCELLED_RUN,
  CATALOGS,
  COMMITS,
  DISCOVERY_POLICIES,
  DISCOVERY_POLICY_ATTACHMENTS,
  DISCOVERY_POLICY_VERSIONS,
  effectivePolicies,
  ESCALATED_RUN,
  inFlightRun,
  MAINTAINED_ORDERS,
  MAINTAINED_TABLES,
  NAMESPACES,
  OLDER_RUN,
  ORDERS,
  ORDERS_CURRENT_METRICS,
  ORDERS_METRIC_TRENDS,
  ORDERS_PROPERTIES,
  ORDERS_SCHEMA_VERSIONS,
  ORDERS_SPEC_VERSIONS,
  ordersSchemaComparison,
  ordersSpecComparison,
  PARTITION_SCOPE_RUN,
  pendingRun,
  PLATFORM_SETTINGS,
  POLICIES,
  POLICY_ATTACHMENTS,
  QUEUE_TIMEOUT_RUN,
  RECONCILIATIONS,
  RETAIL,
  RETAIL_TABLES,
  RETRY_WAITING_RUN,
  RUNS,
  SALES_TABLES,
  SCANNED_CATALOGS,
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
    // Every run of the story data by its id, the older one the list never returns included; any other id is gone.
    getGetTableMaintenanceRunMockHandler(({ params }) => {
      const runs = [...RUNS, ESCALATED_RUN, PARTITION_SCOPE_RUN, OLDER_RUN, QUEUE_TIMEOUT_RUN, RETRY_WAITING_RUN, CANCELLED_RUN, inFlightRun(), pendingRun()];
      const run = runs.find((r) => r.run_id === params.runId);
      if (run === undefined) throw HttpResponse.json({ detail: `run ${params.runId} not found` }, { status: 404 });
      return run;
    }),
    getGetPlatformSettingsMockHandler(PLATFORM_SETTINGS),
    // Every reconciliation of the story data by its id; any other id is gone.
    getGetTableReconciliationMockHandler(({ params }) => {
      const record = RECONCILIATIONS.find((r) => r.reconciliation_id === params.reconciliationId);
      if (record === undefined) {
        throw HttpResponse.json({ detail: `table reconciliation ${params.reconciliationId} not found` }, { status: 404 });
      }
      return record;
    }),
    getListTableReconciliationsMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      const before = query.get("before");
      const limit = Number(query.get("limit") ?? 50);
      return RECONCILIATIONS.filter(
        (r) => before === null || Date.parse(r.reconciled_at) < Date.parse(before),
      ).slice(0, limit);
    }),
    getListTableDiscoveryPoliciesMockHandler({ policies: DISCOVERY_POLICIES }),
    getGetTableDiscoveryPolicyMockHandler(({ params }) => {
      const found = DISCOVERY_POLICIES.find((p) => p.name === params.name);
      if (found === undefined) {
        throw HttpResponse.json({ detail: `discovery policy ${params.name} not found` }, { status: 404 });
      }
      return found;
    }),
    getGetTableDiscoveryPolicyVersionMockHandler(({ params }) => {
      const found = DISCOVERY_POLICIES.find((p) => p.name === params.name);
      if (found === undefined) {
        throw HttpResponse.json({ detail: `discovery policy ${params.name} not found` }, { status: 404 });
      }
      const version = Number(params.version);
      if (version === found.version) return found;
      const kept = DISCOVERY_POLICY_VERSIONS.find((v) => v.name === params.name && v.version === version);
      if (kept === undefined) {
        throw HttpResponse.json(
          { detail: `version ${params.version} of discovery policy ${params.name} not found` },
          { status: 404 },
        );
      }
      return kept;
    }),
    // The saved policy moves one version on; a rule sent without an id gets one, as the server does.
    getUpdateTableDiscoveryPolicyMockHandler(async ({ params, request }) => {
      const found = DISCOVERY_POLICIES.find((p) => p.name === params.name) ?? SALES_TABLES;
      const body = await request.json();
      return {
        ...found,
        description: body.description,
        no_match_outcome: body.no_match_outcome,
        rules: body.rules.map((rule, index) => ({
          id: rule.id ?? `dr-01m7s6c3tqee0rhg00xz1dka${index}`,
          outcome: rule.outcome,
          conditions: rule.conditions,
        })),
        version: found.version + 1,
        updated_at: "2026-11-09T09:00:00Z",
      };
    }),
    getCreateTableDiscoveryPolicyMockHandler(async ({ request }) => ({
      ...DISCOVERY_POLICIES[0]!,
      id: "dp-01m7s6c3tqee0rhg00xry2zqqw",
      is_default: false,
      description: "",
      ...((await request.json()) as object),
      version: 1,
    })),
    getDeleteTableDiscoveryPolicyMockHandler(),
    getListTableDiscoveryPolicyAttachmentsMockHandler(({ params }) => ({
      attachments: DISCOVERY_POLICY_ATTACHMENTS.filter((attachment) => attachment.policy_name === params.name),
    })),
    getAttachTableDiscoveryPolicyMockHandler(async ({ params, request }) => ({
      id: "da-01m7s6c3tqee0rhg00xry2zqqy",
      policy_id: (DISCOVERY_POLICIES.find((p) => p.name === params.name) ?? SALES_TABLES).id,
      policy_name: params.name,
      target: { ...(await request.json()).target, table_uuid: null },
      attached_at: "2026-11-09T09:00:00Z",
    })),
    getDetachTableDiscoveryPolicyMockHandler(),
    getListScannedCatalogsMockHandler(SCANNED_CATALOGS),
    getListTableMaintenancePoliciesMockHandler({ policies: POLICIES }),
    getListTableMaintenancePolicyAttachmentsMockHandler(({ params }) => ({
      attachments: POLICY_ATTACHMENTS.filter((attachment) => attachment.policy_name === params.name),
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
    getGetEffectivePoliciesMockHandler(({ request }) => {
      const query = new URL(request.url).searchParams;
      return effectivePolicies(
        query.get("catalog") ?? "",
        query.get("namespace")?.split(".") ?? [],
        query.get("table") ?? undefined,
      );
    }),
    getGetTableEffectivePoliciesMockHandler(effectivePolicies(ORDERS.catalog, ORDERS.namespace, ORDERS.name)),
    getAttachTableMaintenancePolicyMockHandler(async ({ params, request }) => ({
      id: "pa-01m7sdb2kq9e4z5r7t8vwx3y6c",
      policy_id: (POLICIES.find((p) => p.name === params.name) ?? POLICIES[0]!).id,
      policy_name: params.name,
      target: { ...((await request.json()).target), table_uuid: null },
      attached_at: "2026-11-12T09:00:00Z",
    })),
    getDetachTableMaintenancePolicyMockHandler(),
  ];
}
