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
    <div className="rounded-lg border border-border p-6 text-sm">
      <p className="font-medium">Maintenance does not manage this table</p>
      <p className="mt-1 text-muted-foreground">
        Reason: <span>{MESSAGES[reason]}</span>
        {reason === "not-found" && (
          <>
            {" "}
            (see <Link to="/discovery-rules" className="underline hover:text-foreground">Discovery rules</Link>)
          </>
        )}
      </p>
    </div>
  );
}
