import { Banner, DescriptionList, DiffList, Panel, TextLink } from "@retail-lakehouse/design-system";
import { useId, useState } from "react";
import { Link, useParams } from "react-router";
import { useGetTableDiscoveryPolicyVersion } from "@/api/generated/discovery-policies/discovery-policies";
import type { TableDiscoveryPolicyVersionApiResponse } from "@/api/generated/model";
import { DiscoveryRulesTable } from "@/components/DiscoveryRulesTable";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage, formatTimestamp } from "@/format";
import { discoveryPoliciesPath, discoveryPolicyPath } from "@/lib/discoveryPolicyPaths";
import { discoveryPolicyChanges } from "@/lib/discoveryPolicyChanges";
import { draftFromPolicy } from "@/lib/discoveryPolicyDraft";

type Version = TableDiscoveryPolicyVersionApiResponse;

// The version against the one before it, read here, so the page needs no comparison route.
function Changes({ name, current }: { name: string; current: Version }) {
  const headingId = useId();
  const [onlyChanges, setOnlyChanges] = useState(true);
  const previousNumber = current.version - 1;
  const hasPrevious = previousNumber >= 1;
  const previous = useGetTableDiscoveryPolicyVersion(name, previousNumber, { query: { enabled: hasPrevious } });
  const title = hasPrevious ? `Changes from v${previousNumber}` : "Changes";

  let body;
  if (!hasPrevious) body = <p className="type-body-medium text-on-surface-variant">First version</p>;
  else if (previous.isError) {
    body = <Banner type="negative" title={`Could not load v${previousNumber} to compare with: ${errorMessage(previous.error)}`} />;
  } else if (previous.data === undefined) body = <PanelSkeleton label={`Loading v${previousNumber}`} />;
  else {
    body = (
      <DiffList
        caption={title}
        items={discoveryPolicyChanges(previous.data, current)}
        onlyChanges={onlyChanges}
        onOnlyChangesChange={setOnlyChanges}
        noChangesState={`Nothing changed from v${previousNumber}.`}
      />
    );
  }
  return (
    <section aria-labelledby={headingId} className="flex min-w-0 flex-col gap-3">
      <h2 id={headingId} className="type-title-small">
        {title}
      </h2>
      {body}
    </section>
  );
}

// One kept version of a discovery policy, as a table's Overview names it. A version never changes,
// so the page only reads; edits go through the policy's own page.
export function DiscoveryPolicyVersionPage() {
  const { name = "", version: param = "" } = useParams();
  const version = Number(param);
  const valid = /^\d+$/.test(param);
  const title = `${name} v${param}`;
  const query = useGetTableDiscoveryPolicyVersion(name, version, { query: { enabled: valid } });

  const header = (
    <PageHeader
      title={title}
      breadcrumbs={[
        { label: "Discovery policies", to: discoveryPoliciesPath() },
        { label: name, to: discoveryPolicyPath(name) },
        { label: title },
      ]}
    >
      {query.data !== undefined && (
        <span>
          Saved <time dateTime={query.data.created_at}>{formatTimestamp(query.data.created_at)}</time>. A saved version
          cannot change; edit the policy on{" "}
          <TextLink asChild inline>
            <Link to={discoveryPolicyPath(name)}>its page</Link>
          </TextLink>
          .
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
  const content = draftFromPolicy(query.data);
  return (
    <section className="flex flex-col gap-4">
      {header}
      <Panel title="Policy">
        <DescriptionList
          items={[
            {
              term: "Description",
              description: content.description || <span className="text-on-surface-variant">—</span>,
            },
          ]}
        />
      </Panel>
      <DiscoveryRulesTable rules={content.rules} />
      <Changes key={query.data.version} name={name} current={query.data} />
    </section>
  );
}
