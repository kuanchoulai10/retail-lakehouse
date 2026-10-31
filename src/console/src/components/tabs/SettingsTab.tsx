import { PanelSkeleton } from "@/components/PanelSkeleton";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../../api/client";
import type { TableApiResponse } from "../../api/types";
import { Alert } from "@/components/ui/alert";
import { errorMessage } from "../../format";
import { SettingsForm } from "../SettingsForm";

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
    return (
      <Alert variant="destructive">Could not load settings: {errorMessage(table.error)}</Alert>
    );
  }
  return <SettingsForm key={table.data.updated_at} table={table.data} />;
}
