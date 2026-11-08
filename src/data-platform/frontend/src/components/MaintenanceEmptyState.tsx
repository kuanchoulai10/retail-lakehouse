import { EmptyState } from "@retail-lakehouse/design-system";
import { Link } from "react-router";

export type MaintenanceEmptyReason = "catalog-not-covered" | "not-found" | "excluded" | "dropped";

const MESSAGES: Record<MaintenanceEmptyReason, string> = {
  "catalog-not-covered": "this catalog is not covered by maintenance",
  "not-found": "no discovery rule includes this table",
  excluded: "excluded from maintenance by hand",
  dropped: "maintenance recorded this table as dropped",
};

export function MaintenanceEmptyState({ reason }: { reason: MaintenanceEmptyReason }) {
  return (
    <EmptyState
      className="rounded-lg border border-outline"
      title="Maintenance does not manage this table"
      description={
        <>
          Reason: <span>{MESSAGES[reason]}</span>
          {reason === "not-found" && (
            <>
              {" "}
              (see{" "}
              <Link to="/discovery-rules" className="underline underline-offset-2 hover:text-on-surface">
                Discovery rules
              </Link>
              )
            </>
          )}
        </>
      }
    />
  );
}
