import { Banner } from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { useListTableMaintenanceRuns } from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import {
  getListTableCommitsQueryKey,
  listTableCommits,
  useGetTableHealth,
  useGetTableStorage,
  useListTableCommits,
} from "@/api/generated/tables/tables";
import { errorMessage } from "@/format";
import { PanelSkeleton } from "@/components/PanelSkeleton";
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
    <Banner type="negative" title={`Could not load ${what}: ${errorMessage(error)}`} />
  );
}

// The maintenance half of the table Overview: health, storage, freshness, commits and runs.
export function MaintenancePanels({ tableUuid, lastCommittedAt }: Props) {
  const health = useGetTableHealth(tableUuid);
  const storage = useGetTableStorage(tableUuid);
  const freshness = useQuery({
    // The last day as of each fetch, so a refetch moves the window; under the commits key prefix.
    queryKey: [...getListTableCommitsQueryKey(tableUuid), "last-day"],
    queryFn: async ({ signal }) => {
      const now = new Date();
      const since = new Date(now.getTime() - DAY_MS).toISOString();
      const commits = await listTableCommits(tableUuid, { since, limit: 1000 }, { signal });
      return { commits, now };
    },
  });
  const recent = useListTableCommits(tableUuid);
  const runs = useListTableMaintenanceRuns(tableUuid);

  return (
    <div className="grid grid-cols-1 gap-4">
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        <div className="grid grid-cols-1 gap-4">
          {health.isPending && <PanelSkeleton label="Loading health…" />}
          {health.isError && <Failure what="health" error={health.error} />}
          {health.data && <HealthPanel tableUuid={tableUuid} health={health.data} />}
        </div>
        <div className="grid grid-cols-1 gap-4">
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
