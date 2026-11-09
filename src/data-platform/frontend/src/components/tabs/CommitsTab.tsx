import {
  Banner,
  DatePicker,
  IconButton,
  IconCheck,
  IconCopy,
  IconDots,
  IconGitCommit,
  List,
  Select,
  Tooltip,
} from "@retail-lakehouse/design-system";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { ListTableCommitsWriter, type TableCommitApiResponse } from "@/api/generated/model";
import { useListTableCommits } from "@/api/generated/tables/tables";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useCommitFilters, type CommitFilters } from "@/components/tabs/useCommitFilters";
import { errorMessage, formatCount, formatRelativeTime, formatTimestamp } from "@/format";
import { writerLabel } from "@/writerLabel";

function sortedNewestFirst(items: TableCommitApiResponse[]): TableCommitApiResponse[] {
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at));
}

const DAY_FORMAT = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

type CommitDay = { label: string; commits: TableCommitApiResponse[] };

// Commits are already newest first, so the days come out newest first too.
function groupedByDay(commits: TableCommitApiResponse[]): CommitDay[] {
  const days: CommitDay[] = [];
  for (const commit of commits) {
    const label = `Commits on ${DAY_FORMAT.format(new Date(commit.committed_at))}`;
    const last = days.at(-1);
    if (last?.label === label) last.commits.push(commit);
    else days.push({ label, commits: [commit] });
  }
  return days;
}

function counted(value: number, noun: string): string {
  return `${formatCount(value)} ${noun}${value === 1 ? "" : "s"}`;
}

// What a commit changed, in the words of a commit message: "1,200 rows added in 4 files".
function changeSummary(commit: TableCommitApiResponse): string[] {
  const changes: string[] = [];
  const sides = [
    { rows: commit.added_records, files: commit.added_data_files, verb: "added", preposition: "in" },
    { rows: commit.deleted_records, files: commit.deleted_data_files, verb: "removed", preposition: "from" },
  ];
  for (const { rows, files, verb, preposition } of sides) {
    const fileCount = files ?? 0;
    if (rows) {
      const where = fileCount > 0 ? ` ${preposition} ${counted(fileCount, "file")}` : "";
      changes.push(`${counted(rows, "row")} ${verb}${where}`);
    } else if (fileCount > 0) {
      changes.push(`${counted(fileCount, "file")} ${verb}`);
    }
  }
  return changes;
}

function commitTitle(commit: TableCommitApiResponse): string {
  const operation = commit.operation ?? "commit";
  const name = operation.charAt(0).toUpperCase() + operation.slice(1);
  const changes = changeSummary(commit);
  return changes.length > 0 ? `${name}: ${changes.join(", ")}` : name;
}

// Snapshot ids are random 64-bit numbers, so like a git hash the first seven digits name a
// commit well enough to read; the full id is in the tooltip, the details and the copy button.
const SHORT_ID_LENGTH = 7;

function CopySnapshotId({ snapshotId }: { snapshotId: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  return (
    <Tooltip content={copied ? "Copied" : "Copy snapshot id"}>
      <IconButton
        styleType="ghost"
        shape="rectangle"
        aria-label={`Copy snapshot id ${snapshotId}`}
        icon={copied ? <IconCheck /> : <IconCopy />}
        onClick={() => {
          void navigator.clipboard.writeText(snapshotId).then(() => setCopied(true));
        }}
      />
    </Tooltip>
  );
}

function CommitDetail({ id, commit }: { id: string; commit: TableCommitApiResponse }) {
  return (
    <div id={id} className="border-t border-outline px-3 py-2">
      <p className="type-code">Snapshot id: {commit.snapshot_id}</p>
      <p className="type-code">Parent id: {commit.parent_id ?? "—"}</p>
      <pre className="type-code mt-2 overflow-x-auto rounded-md bg-surface-container-dim p-2">
        {JSON.stringify(commit.summary, null, 2)}
      </pre>
    </div>
  );
}

function CommitRow({ commit }: { commit: TableCommitApiResponse }) {
  const [open, setOpen] = useState(false);
  const detailId = useId();

  return (
    <li>
      <div className="flex flex-col gap-1 px-3 py-2 sm:flex-row sm:items-center sm:gap-3">
        <div className="min-w-0 flex-1">
          <p className="type-label-large break-words text-on-surface">{commitTitle(commit)}</p>
          <p className="type-body-small text-on-surface-variant">
            {writerLabel(commit.writer)} committed{" "}
            <time dateTime={commit.committed_at} title={formatTimestamp(commit.committed_at)}>
              {formatRelativeTime(commit.committed_at)}
            </time>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <span className="type-code font-mono text-on-surface-variant" title={commit.snapshot_id}>
            {commit.snapshot_id.slice(0, SHORT_ID_LENGTH)}
          </span>
          <CopySnapshotId snapshotId={commit.snapshot_id} />
          <Tooltip content={open ? "Hide details" : "Show details"}>
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Details of commit ${commit.snapshot_id}`}
              aria-expanded={open}
              aria-controls={open ? detailId : undefined}
              icon={<IconDots />}
              onClick={() => setOpen((value) => !value)}
            />
          </Tooltip>
        </div>
      </div>
      {open && <CommitDetail id={detailId} commit={commit} />}
    </li>
  );
}

// One day of the history, drawn as GitHub draws it: a commit mark on a line running down the
// left, the day's commits in one box beside it.
function CommitDaySection({ day }: { day: CommitDay }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="relative pb-6 pl-9 last:pb-0">
      <span aria-hidden="true" className="absolute top-6 bottom-0 left-3 border-l border-outline" />
      <IconGitCommit aria-hidden="true" className="absolute top-0 left-0 size-6 text-on-surface-variant" />
      <h2 id={headingId} className="type-label-large leading-6 text-on-surface-variant">
        {day.label}
      </h2>
      <List className="mt-2 divide-y divide-outline rounded-md border border-outline bg-surface">
        {day.commits.map((commit) => (
          <CommitRow key={commit.snapshot_id} commit={commit} />
        ))}
      </List>
    </section>
  );
}

const ALL_WRITERS = "all";

const WRITER_ITEMS = [
  { value: ALL_WRITERS, label: "All writers" },
  ...Object.values(ListTableCommitsWriter).map((writer) => ({ value: writer, label: writerLabel(writer) })),
];

// GitHub's commits page filters by author and by a date range; a table's history filters by the
// writer that made the commit and by the days it was made on.
function CommitFilterBar({ filters }: { filters: CommitFilters }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
      <DatePicker
        label="Committed between"
        hideLabel
        selectionMode="range"
        value={filters.range}
        onValueChange={filters.setRange}
        maxDate={new Date()}
        className="sm:w-80"
      />
      <Select
        label="Writer"
        hideLabel
        items={WRITER_ITEMS}
        value={filters.writer ?? ALL_WRITERS}
        onValueChange={(value) =>
          filters.setWriter(Object.values(ListTableCommitsWriter).find((writer) => writer === value) ?? undefined)
        }
        className="sm:w-48"
      />
    </div>
  );
}

function CommitHistory({ tableUuid, filters }: { tableUuid: string; filters: CommitFilters }) {
  const commits = useListTableCommits(tableUuid, filters.params, { query: { placeholderData: keepPreviousData } });

  if (commits.isPending) return <PanelSkeleton label="Loading commits…" />;
  if (commits.isError) {
    return <Banner type="negative" title={`Could not load commits: ${errorMessage(commits.error)}`} />;
  }
  const days = groupedByDay(sortedNewestFirst(commits.data.items));
  return (
    <>
      {days.length === 0 ? (
        <p className="type-body-medium text-on-surface-variant">
          {filters.isFiltered ? "No commits match these filters." : "No commits."}
        </p>
      ) : (
        days.map((day) => <CommitDaySection key={day.label} day={day} />)
      )}
      {commits.data.truncated && (
        <p className="type-body-small mt-3 text-notice-text">Showing the newest commits only.</p>
      )}
    </>
  );
}

export function CommitsTab({ tableUuid }: { tableUuid: string }) {
  const filters = useCommitFilters();
  return (
    <>
      <CommitFilterBar filters={filters} />
      <CommitHistory tableUuid={tableUuid} filters={filters} />
    </>
  );
}
