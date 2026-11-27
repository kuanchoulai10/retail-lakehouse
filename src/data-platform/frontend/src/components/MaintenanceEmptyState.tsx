import { EmptyState, TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";
import { discoveryPoliciesPath } from "@/lib/discoveryPolicyPaths";

export type MaintenanceEmptyReason =
  | "catalog-not-scanned"
  | "catalog-cannot-access"
  | "not-found"
  | "undecided"
  | "unmanaged"
  | "dropped";

const MESSAGES: Record<MaintenanceEmptyReason, string> = {
  "catalog-not-scanned": "no discovery policy in this catalog manages tables",
  "catalog-cannot-access": "discovery cannot read this catalog with the platform's catalog credential",
  "not-found": "discovery has not found this table yet",
  undecided: "discovery has not decided this table yet",
  unmanaged: "no discovery policy that applies to this table manages it",
  dropped: "maintenance recorded this table as dropped",
};

// Every reason but a dropped table is decided by the discovery policies, or the catalog they read.
const LINKS_TO_POLICIES: ReadonlySet<MaintenanceEmptyReason> = new Set<MaintenanceEmptyReason>([
  "catalog-not-scanned",
  "catalog-cannot-access",
  "not-found",
  "undecided",
  "unmanaged",
]);

export function MaintenanceEmptyState({ reason }: { reason: MaintenanceEmptyReason }) {
  return (
    <EmptyState
      className="rounded-lg border border-outline"
      title="Maintenance does not manage this table"
      description={
        <>
          Reason: <span>{MESSAGES[reason]}</span>
          {LINKS_TO_POLICIES.has(reason) && (
            <>
              {" "}
              (see{" "}
              <TextLink asChild inline>
                <Link to={discoveryPoliciesPath()}>Discovery policies</Link>
              </TextLink>
              )
            </>
          )}
        </>
      }
    />
  );
}
