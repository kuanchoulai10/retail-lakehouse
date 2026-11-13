import { useGetSchedulerSettings } from "@/api/generated/compaction-rounds/compaction-rounds";
import type { SchedulerPriorityApiResponse } from "@/api/generated/model";

// The settings change only with a deploy, so one fetch serves every priority shown on a page.
const SETTINGS_STALE_MS = 5 * 60_000;

// Each priority's weight and SLA from the scheduler settings; undefined until they load or when
// they cannot, so a caller shows the priority alone.
export function useSchedulerPriorities(): SchedulerPriorityApiResponse[] | undefined {
  const settings = useGetSchedulerSettings({ query: { staleTime: SETTINGS_STALE_MS, retry: false } });
  return settings.data?.priorities;
}
