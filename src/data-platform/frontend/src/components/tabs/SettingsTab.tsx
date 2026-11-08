import { Banner } from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { TableApiResponse } from "@/api/types";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { SettingsForm } from "@/components/SettingsForm";
import { errorMessage } from "@/format";

interface Props {
  tableUuid: string;
}

export function SettingsTab({ tableUuid }: Props) {
  const table = useQuery({
    queryKey: ["table", tableUuid],
    queryFn: () => apiGet<TableApiResponse>(`/v1/tables/${tableUuid}`),
  });
  if (table.isPending) return <PanelSkeleton label="Loading settings…" />;
  if (table.isError) {
    return <Banner type="negative" title={`Could not load settings: ${errorMessage(table.error)}`} />;
  }
  return <SettingsForm key={table.data.updated_at} table={table.data} />;
}
