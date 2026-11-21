import {
  Banner,
  DatePicker,
  Drawer,
  IconButton,
  IconDots,
  IconGitCommit,
  List,
  Select,
  TextLink,
  Tooltip,
} from "@retail-lakehouse/design-system";
import { keepPreviousData } from "@tanstack/react-query";
import { useId } from "react";
import { Link } from "react-router";
import { ListTableCommitsWriter, type TableCommitApiResponse } from "@/api/generated/model";
import { useListTableCommits } from "@/api/generated/tables/tables";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { CommitPanel } from "@/components/tabs/CommitPanel";
import { commitTitle } from "@/components/tabs/commitText";
import { CopySnapshotId } from "@/components/tabs/CopySnapshotId";
import { useCommitFilters, type CommitFilters } from "@/components/tabs/useCommitFilters";
import { useOpenRecord } from "@/components/tabs/useOpenRecord";
import { errorMessage, formatRelativeTime, formatTimestamp } from "@/format";
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

// Snapshot ids are random 64-bit numbers, so like a git hash the first seven digits name a
// commit well enough to read; the full id is in the tooltip, the panel and the copy button.
const SHORT_ID_LENGTH = 7;

const REFRESH_FAILED = "Could not refresh. Showing what was last read.";

function CommitRow({
  commit,
  schemaHref,
  isOpen,
  onOpen,
}: {
  commit: TableCommitApiResponse;
  schemaHref: (schemaId: number) => string;
  isOpen: boolean;
  onOpen: () => void;
}) {
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
          {commit.schema_id !== null && (
            <Tooltip content={`Written with schema v${commit.schema_id}`}>
              <TextLink asChild className="type-code font-mono">
                <Link to={schemaHref(commit.schema_id)} aria-label={`Schema v${commit.schema_id}`}>
                  v{commit.schema_id}
                </Link>
              </TextLink>
            </Tooltip>
          )}
          <span className="type-code font-mono text-on-surface-variant" title={commit.snapshot_id}>
            {commit.snapshot_id.slice(0, SHORT_ID_LENGTH)}
          </span>
          <CopySnapshotId snapshotId={commit.snapshot_id} />
          <Tooltip content="Show details">
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Details of commit ${commit.snapshot_id}`}
              aria-haspopup="dialog"
              aria-expanded={isOpen}
              icon={<IconDots />}
              onClick={onOpen}
            />
          </Tooltip>
        </div>
      </div>
    </li>
  );
}

// One day of the history, drawn as GitHub draws it: a commit mark on a line running down the
// left, the day's commits in one box beside it.
function CommitDaySection({
  day,
  schemaHref,
  openId,
  onOpen,
}: {
  day: CommitDay;
  schemaHref: (schemaId: number) => string;
  openId: string | null;
  onOpen: (snapshotId: string) => void;
}) {
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
          <CommitRow
            key={commit.snapshot_id}
            commit={commit}
            schemaHref={schemaHref}
            isOpen={openId === commit.snapshot_id}
            onOpen={() => onOpen(commit.snapshot_id)}
          />
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

function CommitHistory({
  tableUuid,
  filters,
  schemaHref,
}: {
  tableUuid: string;
  filters: CommitFilters;
  schemaHref: (schemaId: number) => string;
}) {
  const { openId, open, close } = useOpenRecord("snapshot");
  const commits = useListTableCommits(tableUuid, filters.params, { query: { placeholderData: keepPreviousData } });

  if (commits.isPending) return <PanelSkeleton label="Loading commits…" />;
  // A failed background read keeps the history it already has on screen; only a first read that fails replaces it.
  if (commits.isError && commits.data === undefined) {
    return <Banner type="negative" title={`Could not load commits: ${errorMessage(commits.error)}`} />;
  }
  const days = groupedByDay(sortedNewestFirst(commits.data.items));
  const shown = openId === null ? undefined : commits.data.items.find((commit) => commit.snapshot_id === openId);
  return (
    <>
      {commits.isError && <Banner type="information" title={REFRESH_FAILED} className="mb-4" />}
      {days.length === 0 ? (
        <p className="type-body-medium text-on-surface-variant">
          {filters.isFiltered ? "No commits match these filters." : "No commits."}
        </p>
      ) : (
        days.map((day) => (
          <CommitDaySection key={day.label} day={day} schemaHref={schemaHref} openId={openId} onOpen={open} />
        ))
      )}
      {commits.data.truncated && (
        <p className="type-body-small mt-3 text-notice-text">Showing the newest commits only.</p>
      )}
      <Drawer
        modal={false}
        contentKey={openId ?? undefined}
        isOpen={openId !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) close();
        }}
        title={shown === undefined ? "Commit" : commitTitle(shown)}
      >
        {shown === undefined ? (
          <p className="type-body-medium text-on-surface-variant">
            This commit is not in the history shown. It may be outside the filters, or expired.
          </p>
        ) : (
          <CommitPanel commit={shown} schemaHref={schemaHref} />
        )}
      </Drawer>
    </>
  );
}

export function CommitsTab({
  tableUuid,
  schemaHref,
}: {
  tableUuid: string;
  schemaHref: (schemaId: number) => string;
}) {
  const filters = useCommitFilters();
  return (
    <>
      <CommitFilterBar filters={filters} />
      <CommitHistory tableUuid={tableUuid} filters={filters} schemaHref={schemaHref} />
    </>
  );
}
