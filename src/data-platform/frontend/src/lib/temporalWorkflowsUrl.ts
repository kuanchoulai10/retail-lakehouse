// The Temporal UI is another app on the same gateway, at `/temporal`. Table workflows carry the
// `TableUuid` search attribute (registered by the Temporal wave), so this lists a table's running ones.
export function temporalWorkflowsUrl(tableUuid: string): string {
  const query = `TableUuid = "${tableUuid}" AND ExecutionStatus = "Running"`;
  return `/temporal/namespaces/default/workflows?query=${encodeURIComponent(query)}`;
}
