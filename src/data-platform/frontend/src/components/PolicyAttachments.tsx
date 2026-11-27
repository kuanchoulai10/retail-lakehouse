import { Badge, Button, Skeleton, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import {
  detachTableMaintenancePolicy,
  useListTableMaintenancePolicyAttachments,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { ListedTableMaintenancePolicyAttachmentApiResponse } from "@/api/generated/model";
import { invalidatePolicyAttachments } from "@/api/invalidatePolicyAttachments";
import { errorMessage } from "@/format";
import { detachPlace } from "@/lib/detachPlace";
import { targetName, targetPagePath } from "@/lib/policyPaths";
import { policyTargetKey } from "@/lib/policyTargetKey";

type Attachment = ListedTableMaintenancePolicyAttachmentApiResponse;

const TARGET_TYPES: Record<string, string> = {
  catalog: "Catalog",
  namespace: "Namespace",
  table: "Table",
};

// Where focus goes once a detach settles: the next place's Detach after the row has gone (the list
// itself when none is left), or back to that row's Detach when the detach was refused.
type Refocus = { kind: "next"; index: number } | { kind: "same"; key: string };

interface RowProps {
  name: string;
  attachment: Attachment;
  detaching: boolean;
  onDetach: () => void;
  detachRef: (button: HTMLButtonElement | null) => void;
}

function Target({ name, attachment, detaching, onDetach, detachRef }: RowProps) {
  const { target, orphaned } = attachment;
  const label = targetName(target);
  const href = orphaned ? null : targetPagePath(target);
  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="text-on-surface-variant">{TARGET_TYPES[target.type] ?? target.type}</span>
      {href === null ? (
        <span className="font-mono break-all">{label}</span>
      ) : (
        <TextLink asChild className="font-mono break-all">
          <Link to={href}>{label}</Link>
        </TextLink>
      )}
      {orphaned && <Badge>No longer in the catalog</Badge>}
      {/* The name starts with the visible label, so voice control finds it (WCAG 2.5.3). */}
      <Button
        ref={detachRef}
        type="button"
        styleType="ghost"
        size="small"
        aria-label={`Detach ${name} from ${label}`}
        disabled={detaching}
        onClick={onDetach}
      >
        Detach
      </Button>
    </li>
  );
}

// Where one maintenance policy is attached, each place with its Detach. The list gives only a count,
// so the places are read only for a policy that has some. A place that left the catalog has no page
// to detach from, so this list is where every place, orphaned or not, is detached; detaching takes
// the policy off that place without deleting it, so it does not ask.
export function PolicyAttachments({ name, count }: { name: string; count: number }) {
  const queryClient = useQueryClient();
  const root = useRef<HTMLDivElement>(null);
  const detachButtons = useRef(new Map<string, HTMLButtonElement>());
  const refocus = useRef<Refocus | null>(null);
  // Bumped once each detach settles, so the refocus below runs even when no render saw it pending.
  const [settled, setSettled] = useState(0);
  const attachments = useListTableMaintenancePolicyAttachments(name, { query: { enabled: count > 0 } });
  const places = attachments.data?.attachments;

  const detach = useMutation({
    mutationFn: (attachment: Attachment) => detachTableMaintenancePolicy(name, detachPlace(attachment.target)),
    // A write can fail after part of it landed, so the list is read again either way.
    onSettled: async (_result, error, attachment) => {
      const key = policyTargetKey(attachment.target);
      const index = places?.findIndex((place) => policyTargetKey(place.target) === key) ?? 0;
      await invalidatePolicyAttachments(queryClient, [name]);
      refocus.current = error === null ? { kind: "next", index: Math.max(index, 0) } : { kind: "same", key };
      setSettled((count) => count + 1);
    },
  });

  useEffect(() => {
    const wanted = refocus.current;
    if (detach.isPending || wanted === null) return;
    refocus.current = null;
    if (wanted.kind === "same") {
      detachButtons.current.get(wanted.key)?.focus();
      return;
    }
    const remaining = places ?? [];
    const next = remaining[Math.min(wanted.index, remaining.length - 1)];
    const button = next === undefined ? undefined : detachButtons.current.get(policyTargetKey(next.target));
    (button ?? root.current)?.focus();
  }, [settled, detach.isPending, places]);

  let body;
  if (count === 0 || places?.length === 0) {
    body = <span className="text-on-surface-variant">Not attached</span>;
  } else if (attachments.isPending) {
    body = (
      <>
        <Skeleton className="h-4 w-32" />
        <span className="sr-only">Loading where {name} is attached</span>
      </>
    );
  } else if (attachments.isError) {
    body = <span className="text-negative-text">Could not load attachments: {errorMessage(attachments.error)}</span>;
  } else {
    body = (
      <ul className="m-0 flex list-none flex-col gap-1 p-0">
        {attachments.data.attachments.map((attachment) => {
          const key = policyTargetKey(attachment.target);
          return (
            <Target
              key={key}
              name={name}
              attachment={attachment}
              detaching={detach.isPending}
              onDetach={() => detach.mutate(attachment)}
              detachRef={(button) => {
                if (button === null) detachButtons.current.delete(key);
                else detachButtons.current.set(key, button);
              }}
            />
          );
        })}
      </ul>
    );
  }

  return (
    <div
      ref={root}
      role="group"
      aria-label={`Where ${name} is attached`}
      tabIndex={-1}
      className="flex flex-col gap-1 rounded-sm outline-none focus-visible:outline-2 focus-visible:outline-focus-ring"
    >
      {detach.isError && (
        <p role="alert" className="text-negative-text">
          Could not detach {name} from {targetName(detach.variables.target)}: {errorMessage(detach.error)}
        </p>
      )}
      {body}
    </div>
  );
}
