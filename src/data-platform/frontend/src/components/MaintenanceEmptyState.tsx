import { EmptyState, TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";

export type MaintenanceEmptyReason = "catalog-not-covered" | "not-found" | "unmanaged" | "dropped";

const MESSAGES: Record<MaintenanceEmptyReason, string> = {
  "catalog-not-covered": "this catalog is not covered by maintenance",
  "not-found": "no discovery rule includes this table",
  unmanaged: "the discovery rules do not include this table",
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
          {(reason === "not-found" || reason === "unmanaged") && (
            <>
              {" "}
              (see{" "}
              <TextLink asChild inline>
                <Link to="/discovery-rules">
                  Discovery rules
                </Link>
              </TextLink>
              )
            </>
          )}
        </>
      }
    />
  );
}
