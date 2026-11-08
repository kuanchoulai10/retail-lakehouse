import { Banner } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { TableApiResponse } from "@/api/types";
import { MaintenanceEmptyState } from "@/components/MaintenanceEmptyState";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage } from "@/format";
import type { TableMaintenanceState } from "@/lib/tableMaintenanceState";

interface Props {
  state: TableMaintenanceState;
  children: (table: TableApiResponse) => ReactNode;
}

// Every maintenance section of the table page goes through here, so an unmanaged table shows
// the same empty state on each of them.
export function MaintenanceGate({ state, children }: Props) {
  switch (state.kind) {
    case "loading":
      return <PanelSkeleton label="Loading maintenance…" />;
    case "failed":
      return (
        <Banner type="negative" title={`Could not load maintenance: ${errorMessage(state.error)}`} />
      );
    case "unmanaged":
      return <MaintenanceEmptyState reason={state.reason} />;
    case "managed":
      return children(state.table);
  }
}
