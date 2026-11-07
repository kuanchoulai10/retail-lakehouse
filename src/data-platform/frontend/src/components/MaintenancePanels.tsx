import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type {
  TableCommitsApiResponse,
  TableHealthApiResponse,
  TableMaintenanceRunApiResponse,
  TableStorageApiResponse,
} from "@/api/types";
import { errorMessage } from "@/format";
import { FreshnessPanel } from "@/components/FreshnessPanel";
import { HealthPanel } from "@/components/HealthPanel";
import { LastRunPanel } from "@/components/LastRunPanel";
import { RecentCommitsPanel } from "@/components/RecentCommitsPanel";
import { StoragePanel } from "@/components/StoragePanel";

const DAY_MS = 24 * 3_600_000;

interface Props {
  tableUuid: string;
  // When the current snapshot was committed, from the catalog; null for a table with none.
  lastCommittedAt: string | null;
}

function Failure({ what, error }: { what: string; error: unknown }) {
  return (
    <p role="alert" className="text-sm text-destructive">
      {`Could not load ${what}: ${errorMessage(error)}`}
    </p>
  );
}

// The maintenance half of the table Overview: health, storage, freshness, commits and runs.
export function MaintenancePanels({ tableUuid, lastCommittedAt }: Props) {
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
    <div className="grid gap-4">
      <div className="grid items-start gap-4 lg:grid-cols-2">
        <div className="grid gap-4">
          {health.isPending && <PanelSkeleton label="Loading health…" />}
          {health.isError && <Failure what="health" error={health.error} />}
          {health.data && <HealthPanel tableUuid={tableUuid} health={health.data} />}
        </div>
        <div className="grid gap-4">
          {storage.isPending && <PanelSkeleton label="Loading storage…" />}
          {storage.isError && <Failure what="storage" error={storage.error} />}
          {storage.data && <StoragePanel storage={storage.data} />}
        </div>
      </div>

      {freshness.isPending && <PanelSkeleton label="Loading freshness…" />}
      {freshness.isError && <Failure what="freshness" error={freshness.error} />}
      {freshness.data && (
        <FreshnessPanel
          commits={freshness.data.commits.items}
          truncated={freshness.data.commits.truncated}
          now={freshness.data.now}
          lastCommittedAt={lastCommittedAt}
        />
      )}

      {recent.isPending && <PanelSkeleton label="Loading commits…" />}
      {recent.isError && <Failure what="commits" error={recent.error} />}
      {recent.data && <RecentCommitsPanel commits={recent.data.items} />}

      {runs.isPending && <PanelSkeleton label="Loading runs…" />}
      {runs.isError && <Failure what="maintenance runs" error={runs.error} />}
      {runs.data && <LastRunPanel runs={runs.data} />}
    </div>
  );
}
