import { Banner, TextLink } from "@retail-lakehouse/design-system";
import { Link, useParams } from "react-router";
import { useGetTableMaintenancePolicyVersion } from "@/api/generated/maintenance-policies/maintenance-policies";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PolicySummary } from "@/components/PolicySummary";
import { errorMessage, formatTimestamp } from "@/format";
import { policiesPath } from "@/lib/policyPaths";

// One saved version of a policy, as reconciliation records and the applicable-policy panels
// name it. A version never changes, so the page only reads; edits go through the Policies page.
export function PolicyVersionPage() {
  const { name = "", version: param = "" } = useParams();
  const version = Number(param);
  const valid = /^\d+$/.test(param);
  const title = `${name} v${param}`;
  const query = useGetTableMaintenancePolicyVersion(name, version, { query: { enabled: valid } });

  const header = (
    <PageHeader title={title} breadcrumbs={[{ label: "Policies", to: policiesPath() }, { label: title }]}>
      {query.data !== undefined && (
        <span>
          Saved <time dateTime={query.data.created_at}>{formatTimestamp(query.data.created_at)}</time>. A saved version
          cannot change; edit the policy on the{" "}
          <TextLink asChild inline>
            <Link to={policiesPath()}>Policies</Link>
          </TextLink>{" "}
          page.
        </span>
      )}
    </PageHeader>
  );

  if (!valid) {
    return (
      <section>
        {header}
        <Banner type="negative" title={`Could not load ${title}: a version is a whole number.`} />
      </section>
    );
  }
  if (query.isPending) return <PanelSkeleton label={`Loading ${title}…`} />;
  if (query.isError) {
    return (
      <section>
        {header}
        <Banner type="negative" title={`Could not load ${title}: ${errorMessage(query.error)}`} />
      </section>
    );
  }
  const policy = query.data;
  return (
    <section>
      {header}
      <PolicySummary
        description={policy.description}
        reconcileIntervalSeconds={policy.reconcile_interval_seconds}
        dryRun={policy.dry_run}
        operations={policy.operations}
      />
    </section>
  );
}
