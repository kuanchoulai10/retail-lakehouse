// A run or attempt in one of these states still has work to do.
const IN_FLIGHT_STATUSES = ["pending", "queued", "running"];

export function isInFlightStatus(status: string): boolean {
  return IN_FLIGHT_STATUSES.includes(status);
}
