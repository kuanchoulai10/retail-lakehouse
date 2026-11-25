// A run or attempt in one of these four states still has work to do: a run in retry_waiting has
// failed an attempt and waits out its backoff before the next one.
const IN_FLIGHT_STATUSES = ["pending", "queued", "running", "retry_waiting"];

export function isInFlightStatus(status: string): boolean {
  return IN_FLIGHT_STATUSES.includes(status);
}
