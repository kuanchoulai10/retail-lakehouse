import { Banner, DiffList, Panel, Select, type DiffListItem } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { CatalogTableApiResponse } from "@/api/generated/model";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { VersionList } from "@/components/VersionList";
import { errorMessage } from "@/format";

const PREVIOUS = "previous";

export type QueryState<T> = { data: T | undefined; isError: boolean; error: unknown };

export type HistoryVersion = {
  id: number;
  previousId: number | null;
  summary: string;
  badge?: string;
};

export type VersionHistory = {
  // The version the table runs: the current schema, the default partition spec.
  defaultId: number;
  // Newest (highest id) first.
  versions: HistoryVersion[];
};

interface Props<Comparison> {
  table: CatalogTableApiResponse;
  // "Schema" and "schema", "Partition spec" and "partition spec": how the panel and its texts name a version.
  title: string;
  noun: string;
  // "current schema", "default spec": what the panel shows when the url names a version the table lacks.
  defaultName: string;
  history: QueryState<VersionHistory>;
  // The url's choices; an id the table does not have reads as no choice.
  chosenId: number | undefined;
  chosenBaseId: number | undefined;
  onlyChanges: boolean;
  onChoose: (id: number) => void;
  onChooseBase: (id: number | undefined) => void;
  onOnlyChangesChange: (onlyChanges: boolean) => void;
  useComparison: (table: CatalogTableApiResponse, id: number, baseId: number | undefined) => QueryState<Comparison>;
  toItems: (comparison: Comparison) => DiffListItem[];
  emptyState?: ReactNode;
}

function VersionHistoryView<Comparison>({
  table,
  title,
  noun,
  defaultName,
  history,
  chosenId,
  chosenBaseId,
  onlyChanges,
  onChoose,
  onChooseBase,
  onOnlyChangesChange,
  useComparison,
  toItems,
  emptyState,
}: Omit<Props<Comparison>, "history"> & { history: VersionHistory }) {
  const { versions, defaultId } = history;
  const has = (id: number | undefined): id is number => versions.some((version) => version.id === id);
  const selectedId = has(chosenId) ? chosenId : defaultId;
  const baseId = has(chosenBaseId) && chosenBaseId !== selectedId ? chosenBaseId : undefined;
  const previousId = versions.find((version) => version.id === selectedId)?.previousId ?? null;
  const comparison = useComparison(table, selectedId, baseId);
  const missing = chosenId !== undefined && !has(chosenId);

  return (
    <div className="flex flex-col gap-4 md:flex-row">
      <div className="md:w-64 md:shrink-0">
        <VersionList
          label={`${title} versions`}
          versions={versions.map((version) => ({
            id: version.id,
            title: `v${version.id}`,
            description: version.summary,
            ...(version.badge ? { badge: version.badge } : {}),
          }))}
          selectedId={selectedId}
          onSelect={onChoose}
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {missing ? (
          <p className="type-body-small text-on-surface-variant">
            {`${title} v${chosenId} is not in this table's history; showing the ${defaultName} (v${defaultId}).`}
          </p>
        ) : null}
        <Select
          label="Compare with"
          className="md:max-w-xs"
          value={baseId === undefined ? PREVIOUS : String(baseId)}
          onValueChange={(value) => onChooseBase(value === PREVIOUS ? undefined : Number(value))}
          items={[
            { value: PREVIOUS, label: previousId === null ? "No earlier version" : `Previous version (v${previousId})` },
            ...versions
              .filter((version) => version.id !== selectedId)
              .map((version) => ({ value: String(version.id), label: `v${version.id}` })),
          ]}
        />
        {comparison.isError ? (
          <Banner type="negative" title={`Could not load the ${noun} comparison: ${errorMessage(comparison.error)}`} />
        ) : comparison.data === undefined ? (
          <PanelSkeleton label={`Loading the ${noun} comparison`} />
        ) : (
          <DiffList
            caption={`Changes in ${noun} v${selectedId}`}
            items={toItems(comparison.data)}
            onlyChanges={onlyChanges}
            onOnlyChangesChange={onOnlyChangesChange}
            {...(emptyState === undefined ? {} : { emptyState })}
          />
        )}
      </div>
    </div>
  );
}

// Every version of something a table keeps a history of (schemas, partition specs), the one the table
// runs marked, and the comparison of the chosen version with the one before it or with any other. The
// url's choices come in as props; an id the table does not have falls back to the table's own version.
export function VersionHistoryPanel<Comparison>(props: Props<Comparison>) {
  const { title, noun, history } = props;
  return (
    <Panel title={title}>
      {history.isError ? (
        <Banner type="negative" title={`Could not load ${noun} versions: ${errorMessage(history.error)}`} />
      ) : history.data === undefined ? (
        <PanelSkeleton label={`Loading ${noun} versions`} />
      ) : (
        <VersionHistoryView {...props} history={history.data} />
      )}
    </Panel>
  );
}
