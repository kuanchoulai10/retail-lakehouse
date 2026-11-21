import { IconButton, IconCheck, IconCopy, Tooltip } from "@retail-lakehouse/design-system";
import { useEffect, useState } from "react";

export function CopySnapshotId({ snapshotId }: { snapshotId: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  return (
    <Tooltip content={copied ? "Copied" : "Copy snapshot id"}>
      <IconButton
        styleType="ghost"
        shape="rectangle"
        aria-label={`Copy snapshot id ${snapshotId}`}
        icon={copied ? <IconCheck /> : <IconCopy />}
        onClick={() => {
          void navigator.clipboard.writeText(snapshotId).then(() => setCopied(true));
        }}
      />
    </Tooltip>
  );
}
