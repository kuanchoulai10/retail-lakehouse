import type { TableMaintenanceRunApiResponse } from "@/api/generated/model";
import { isInFlightStatus } from "@/lib/isInFlightStatus";

// True while a listed run, or any attempt of it, is still pending, queued, running or waiting to retry.
export function anyRunInFlight(runs: TableMaintenanceRunApiResponse[] | undefined): boolean {
  return (runs ?? []).some(
    (run) => isInFlightStatus(run.status) || run.attempts.some((attempt) => isInFlightStatus(attempt.status)),
  );
}
