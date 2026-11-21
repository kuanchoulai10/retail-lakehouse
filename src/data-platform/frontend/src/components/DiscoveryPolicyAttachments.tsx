import { Badge, Banner, Button, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useRef, useState } from "react";
import { Link } from "react-router";
import {
  detachTableDiscoveryPolicy,
  useListScannedCatalogs,
  useListTableDiscoveryPolicyAttachments,
} from "@/api/generated/discovery-policies/discovery-policies";
import type {
  ListedTableDiscoveryPolicyAttachmentApiResponse,
  ScannedCatalogApiResponse,
} from "@/api/generated/model";
import { invalidateDiscoveryPolicyAttachments } from "@/api/invalidateDiscoveryPolicyAttachments";
import { errorMessage, formatRelativeTime, formatTimestamp } from "@/format";
import { catalogScanState, scanFailureLabel } from "@/lib/catalogScanState";
import { targetName, targetPagePath } from "@/lib/policyPaths";
import { AttachDiscoveryPolicyDialog } from "./AttachDiscoveryPolicyDialog";

type Attachment = ListedTableDiscoveryPolicyAttachmentApiResponse;

const TARGET_TYPES: Record<string, string> = {
  catalog: "Catalog",
  namespace: "Namespace",
  table: "Table",
};

// The scan state of the catalog an attachment is in. The attachment list stays readable when a
// catalog refuses the platform (Ruling R4), and the refusal shows here.
function ScanState({ catalog, scanned }: { catalog: string; scanned: ScannedCatalogApiResponse[] }) {
  const state = catalogScanState(catalog, scanned);
  switch (state.kind) {
    case "scanned":
      return (
        <span>
          Scanned{" "}
          <time dateTime={state.at} title={formatTimestamp(state.at)}>
            {formatRelativeTime(state.at)}
          </time>
        </span>
      );
    case "not-scanned-yet":
      return <span>Not scanned yet</span>;
    case "not-scanned":
      return (
        <span>
          Not scanned: no policy in <span className="font-mono">{catalog}</span> manages tables
        </span>
      );
    case "failed":
      return (
        <span>
          <span className="font-medium text-negative-text">{scanFailureLabel(state.reason)}</span>: {state.detail}
        </span>
      );
  }
}

interface RowProps {
  attachment: Attachment;
  scanned: ScannedCatalogApiResponse[] | null;
  detaching: boolean;
  onDetach: (attachment: Attachment) => void;
}

function AttachmentRow({ attachment, scanned, detaching, onDetach }: RowProps) {
  const { target, orphaned } = attachment;
  const name = targetName(target);
  const href = orphaned ? null : targetPagePath(target);
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-outline py-2">
      <div className="flex min-w-0 flex-col gap-1">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-on-surface-variant">{TARGET_TYPES[target.type] ?? target.type}</span>
          {href === null ? (
            <span className="font-mono break-all">{name}</span>
          ) : (
            <TextLink asChild className="font-mono break-all">
              <Link to={href}>{name}</Link>
            </TextLink>
          )}
          {orphaned && <Badge>Orphaned</Badge>}
        </p>
        {scanned !== null && target.path[0] !== undefined && (
          <p className="type-body-small text-on-surface-variant">
            <ScanState catalog={target.path[0]} scanned={scanned} />
          </p>
        )}
      </div>
      <Button
        type="button"
        styleType="outlined"
        size="small"
        aria-label={`Detach from ${name}`}
        disabled={detaching}
        onClick={() => onDetach(attachment)}
      >
        Detach
      </Button>
    </li>
  );
}

// Where one discovery policy is attached, each target with its catalog's scan state, and the
// attach and detach actions. Detaching removes a mapping, not the policy, so it does not ask.
export function DiscoveryPolicyAttachments({ policyName }: { policyName: string }) {
  const queryClient = useQueryClient();
  const headingId = useId();
  const attachButton = useRef<HTMLButtonElement>(null);
  const [attaching, setAttaching] = useState(false);
  const attachments = useListTableDiscoveryPolicyAttachments(policyName);
  const scanned = useListScannedCatalogs();

  const detach = useMutation({
    mutationFn: (attachment: Attachment) => detachTableDiscoveryPolicy(policyName, attachment.id),
    // A write can fail after part of it landed, so the page refetches either way. The detached row
    // is gone once the list is read again, so focus moves to Attach rather than being lost.
    onSettled: async (_result, error) => {
      await invalidateDiscoveryPolicyAttachments(queryClient);
      if (error === null) attachButton.current?.focus();
    },
  });

  let body;
  if (attachments.isPending) {
    body = (
      <>
        <Skeleton className="h-4 w-48" />
        <span className="sr-only">Loading where {policyName} is attached</span>
      </>
    );
  } else if (attachments.isError) {
    body = (
      <Banner
        type="negative"
        title={`Could not load where ${policyName} is attached: ${errorMessage(attachments.error)}`}
      />
    );
  } else if (attachments.data.attachments.length === 0) {
    body = (
      <p className="type-body-medium text-on-surface-variant">
        Not attached. Attach it to a catalog, namespace or table to apply it.
      </p>
    );
  } else {
    body = (
      <ul className="type-body-medium m-0 flex list-none flex-col p-0">
        {attachments.data.attachments.map((attachment) => (
          <AttachmentRow
            key={attachment.id}
            attachment={attachment}
            scanned={scanned.data?.catalogs ?? null}
            detaching={detach.isPending}
            onDetach={(chosen) => detach.mutate(chosen)}
          />
        ))}
      </ul>
    );
  }

  return (
    <section aria-labelledby={headingId} className="flex min-w-0 flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className="type-title-small">
          Attached to
        </h2>
        <Button
          ref={attachButton}
          type="button"
          size="small"
          onClick={() => {
            detach.reset();
            setAttaching(true);
          }}
        >
          Attach
        </Button>
      </header>
      {detach.isError && (
        <Banner
          type="negative"
          title={`Could not detach from ${targetName(detach.variables.target)}: ${errorMessage(detach.error)}`}
        />
      )}
      {scanned.isError && (
        <Banner type="negative" title={`Could not load each catalog's scan state: ${errorMessage(scanned.error)}`} />
      )}
      {body}
      {attaching && <AttachDiscoveryPolicyDialog policyName={policyName} onClose={() => setAttaching(false)} />}
    </section>
  );
}
