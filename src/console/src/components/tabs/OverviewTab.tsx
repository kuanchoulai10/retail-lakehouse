import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../../api/client";
import type {
  TableCommitsApiResponse,
  TableHealthApiResponse,
  TableMaintenanceRunApiResponse,
  TableMetadataApiResponse,
  TableStorageApiResponse,
} from "../../api/types";
import { errorMessage } from "../../format";
import { FreshnessPanel } from "../FreshnessPanel";
import { HealthPanel } from "../HealthPanel";
import { LastRunPanel } from "../LastRunPanel";
import { RecentCommitsPanel } from "../RecentCommitsPanel";
import { SchemaPanel } from "../SchemaPanel";
import { StoragePanel } from "../StoragePanel";

const DAY_MS = 24 * 3_600_000;

interface Props {
  tableUuid: string;
  metadata: TableMetadataApiResponse;
}

function Failure({ what, error }: { what: string; error: unknown }) {
  return (
    <p role="alert" className="error">
      {`Could not load ${what}: ${errorMessage(error)}`}
    </p>
  );
}

export function OverviewTab({ tableUuid, metadata }: Props) {
  const health = useQuery({
    queryKey: ["health", tableUuid],
    queryFn: () => apiGet<TableHealthApiResponse>(`/v1/tables/${tableUuid}/health`),
  });
  const storage = useQuery({
    queryKey: ["storage", tableUuid],
    queryFn: () => apiGet<TableStorageApiResponse>(`/v1/tables/${tableUuid}/storage`),
  });
  const freshness = useQuery({
    queryKey: ["freshness", tableUuid],
    queryFn: async () => {
      const now = new Date();
      const since = new Date(now.getTime() - DAY_MS).toISOString();
      const commits = await apiGet<TableCommitsApiResponse>(
        `/v1/tables/${tableUuid}/commits?since=${encodeURIComponent(since)}&limit=1000`,
      );
      return { commits, now };
    },
  });
  const recent = useQuery({
    queryKey: ["commits", tableUuid],
    queryFn: () => apiGet<TableCommitsApiResponse>(`/v1/tables/${tableUuid}/commits`),
  });
  const runs = useQuery({
    queryKey: ["runs", tableUuid],
    queryFn: () =>
      apiGet<TableMaintenanceRunApiResponse[]>(`/v1/tables/${tableUuid}/table-maintenance-runs`),
  });

  return (
    <div className="overview">
      {health.isPending && <p>Loading health…</p>}
      {health.isError && <Failure what="health" error={health.error} />}
      {health.data && <HealthPanel tableUuid={tableUuid} health={health.data} />}

      {storage.isPending && <p>Loading storage…</p>}
      {storage.isError && <Failure what="storage" error={storage.error} />}
      {storage.data && <StoragePanel storage={storage.data} />}

      {freshness.isPending && <p>Loading freshness…</p>}
      {freshness.isError && <Failure what="freshness" error={freshness.error} />}
      {freshness.data && (
        <FreshnessPanel
          commits={freshness.data.commits.items}
          truncated={freshness.data.commits.truncated}
          now={freshness.data.now}
          lastCommittedAt={metadata.last_committed_at}
        />
      )}

      <SchemaPanel metadata={metadata} />

      {recent.isPending && <p>Loading commits…</p>}
      {recent.isError && <Failure what="commits" error={recent.error} />}
      {recent.data && <RecentCommitsPanel commits={recent.data.items} />}

      {runs.isPending && <p>Loading runs…</p>}
      {runs.isError && <Failure what="maintenance runs" error={runs.error} />}
      {runs.data && <LastRunPanel runs={runs.data} />}
    </div>
  );
}
