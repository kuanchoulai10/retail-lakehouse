import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link } from "react-router";
import { apiGet } from "@/api/client";
import type {
  TableDiscoveryRuleApiResponse,
  TableDiscoverySettingsApiResponse,
  TableMaintenancePresetApiResponse,
} from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { errorMessage, formatTimestamp } from "@/format";

const COLUMN_COUNT = 6;
const SKELETON_ROWS = 3;

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function pattern(rule: TableDiscoveryRuleApiResponse): string {
  return `${rule.catalog_pattern}.${rule.namespace_pattern}.${rule.table_pattern}`;
}

function byEvaluationOrder(a: TableDiscoveryRuleApiResponse, b: TableDiscoveryRuleApiResponse): number {
  return a.priority - b.priority || a.id.localeCompare(b.id);
}

function DiscoveryState() {
  const settings = useQuery({
    queryKey: ["table-discovery-settings"],
    queryFn: () => apiGet<TableDiscoverySettingsApiResponse>("/v1/table-discovery-settings"),
  });
  if (!settings.isSuccess) return null;
  return <span>{settings.data.enabled ? "Discovery is on" : "Discovery is off"}</span>;
}

export function DiscoveryRulesPage() {
  const rules = useQuery({
    queryKey: ["table-discovery-rules"],
    queryFn: () => apiGet<TableDiscoveryRuleApiResponse[]>("/v1/table-discovery-rules"),
  });
  const presets = useQuery({
    queryKey: ["table-maintenance-presets"],
    queryFn: () => apiGet<TableMaintenancePresetApiResponse[]>("/v1/table-maintenance-presets"),
  });

  const presetNames = useMemo(
    () => new Map((presets.data ?? []).map((preset) => [preset.id, preset.name])),
    [presets.data],
  );
  const ordered = useMemo(() => [...(rules.data ?? [])].sort(byEvaluationOrder), [rules.data]);

  return (
    <section>
      <PageHeader title="Discovery rules">
        <DiscoveryState />
        <span>Lowest priority first; the first enabled rule that matches a table decides.</span>
      </PageHeader>
      {rules.isError && (
        <Alert variant="destructive">
          <AlertDescription>Could not load discovery rules: {errorMessage(rules.error)}</AlertDescription>
        </Alert>
      )}
      {!rules.isError && (
        <div aria-busy={rules.isPending} className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Priority</TableHead>
                <TableHead>Effect</TableHead>
                <TableHead>Pattern</TableHead>
                <TableHead>Preset</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.isPending &&
                Array.from({ length: SKELETON_ROWS }, (_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COLUMN_COUNT }, (_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full max-w-40" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              {rules.isSuccess &&
                ordered.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="tabular-nums">{rule.priority}</TableCell>
                    <TableCell>{capitalise(rule.effect)}</TableCell>
                    <TableCell className="font-mono text-[13px]">{pattern(rule)}</TableCell>
                    <TableCell>
                      {rule.preset_id === null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <Link to={`/presets#preset-${rule.preset_id}`} className="font-mono text-[13px] hover:underline">
                          {presetNames.get(rule.preset_id) ?? rule.preset_id}
                        </Link>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{rule.enabled ? "Enabled" : "Disabled"}</TableCell>
                    <TableCell>
                      <time dateTime={rule.updated_at} className="tabular-nums">
                        {formatTimestamp(rule.updated_at)}
                      </time>
                    </TableCell>
                  </TableRow>
                ))}
              {rules.isSuccess && ordered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={COLUMN_COUNT} className="text-center text-muted-foreground">
                    No discovery rules.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}
