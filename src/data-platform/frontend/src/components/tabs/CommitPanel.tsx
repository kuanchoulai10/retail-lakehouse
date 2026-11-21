import { DescriptionList, type DescriptionListItem, TextLink } from "@retail-lakehouse/design-system";
import { useId } from "react";
import { Link } from "react-router";
import type { TableCommitApiResponse } from "@/api/generated/model";
import { changeSummary } from "@/components/tabs/commitText";
import { CopySnapshotId } from "@/components/tabs/CopySnapshotId";
import { formatTimestamp } from "@/format";
import { writerLabel } from "@/writerLabel";

function fields(commit: TableCommitApiResponse, schemaHref: (schemaId: number) => string): DescriptionListItem[] {
  const changes = changeSummary(commit);
  return [
    {
      term: "Snapshot id",
      description: (
        <span className="flex items-center gap-1">
          <span className="font-mono break-all">{commit.snapshot_id}</span>
          <CopySnapshotId snapshotId={commit.snapshot_id} />
        </span>
      ),
    },
    { term: "Parent", description: <span className="font-mono break-all">{commit.parent_id ?? "—"}</span> },
    {
      term: "Committed",
      description: <time dateTime={commit.committed_at}>{formatTimestamp(commit.committed_at)}</time>,
    },
    { term: "Writer", description: writerLabel(commit.writer) },
    {
      term: "Schema",
      description:
        commit.schema_id === null ? (
          "—"
        ) : (
          <TextLink asChild inline className="font-mono">
            <Link to={schemaHref(commit.schema_id)} aria-label={`Schema v${commit.schema_id}`}>
              v{commit.schema_id}
            </Link>
          </TextLink>
        ),
    },
    {
      term: "Changes",
      description:
        changes.length === 0 ? (
          "—"
        ) : (
          <ul>
            {changes.map((change) => (
              <li key={change}>{change}</li>
            ))}
          </ul>
        ),
    },
  ];
}

// The snapshot summary's keys and values as Iceberg wrote them, in the API's order.
function summaryFields(summary: TableCommitApiResponse["summary"]): DescriptionListItem[] {
  return Object.entries(summary).map(([key, value]) => ({
    term: key,
    description: <span className="font-mono break-all">{String(value)}</span>,
  }));
}

// One commit's facts and its snapshot summary, for the Commits tab's side panel.
export function CommitPanel({
  commit,
  schemaHref,
}: {
  commit: TableCommitApiResponse;
  schemaHref: (schemaId: number) => string;
}) {
  const summaryId = useId();
  const summary = summaryFields(commit.summary);
  return (
    <div className="flex flex-col gap-6">
      <DescriptionList items={fields(commit, schemaHref)} />
      <section aria-labelledby={summaryId} className="flex flex-col gap-2">
        <h3 id={summaryId} className="type-label-large text-on-surface">
          Summary
        </h3>
        {summary.length === 0 ? (
          <p className="type-body-medium text-on-surface-variant">No summary entries.</p>
        ) : (
          <DescriptionList items={summary} className="[&_dt]:font-mono" />
        )}
      </section>
    </div>
  );
}
