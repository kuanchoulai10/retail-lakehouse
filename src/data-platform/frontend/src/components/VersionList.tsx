import { Badge, Button, List, ListItem } from "@retail-lakehouse/design-system";
import { useEffect, useRef, useState } from "react";

export type Version = { id: number; title: string; description: string; badge?: string };

interface Props {
  label: string;
  // Newest first.
  versions: Version[];
  selectedId: number;
  onSelect: (id: number) => void;
  visibleCount?: number;
}

// A long history folds behind a button: the newest few are what people open, and a version that is
// selected (from a link, say) is never hidden.
export function VersionList({ label, versions, selectedId, onSelect, visibleCount = 10 }: Props) {
  const list = useRef<HTMLUListElement>(null);
  const [revealed, setRevealed] = useState(false);
  const hidden = versions.slice(visibleCount);
  const selectedIsHidden = hidden.some((version) => version.id === selectedId);
  const showAll = revealed || selectedIsHidden;
  const shown = showAll ? versions : versions.slice(0, visibleCount);

  // The button that revealed the rest is gone, so focus moves to the first version it revealed.
  useEffect(() => {
    if (revealed) list.current?.querySelectorAll("button")[visibleCount]?.focus();
  }, [revealed, visibleCount]);

  return (
    <div className="flex min-w-0 flex-col gap-1">
      <List ref={list} aria-label={label}>
        {shown.map((version) => (
          <ListItem
            key={version.id}
            title={<span className="type-code">{version.title}</span>}
            description={version.description}
            isSelected={version.id === selectedId}
            onSelect={() => onSelect(version.id)}
            trailingItem={version.badge ? <Badge>{version.badge}</Badge> : undefined}
          />
        ))}
      </List>
      {showAll || hidden.length === 0 ? null : (
        <Button type="button" styleType="ghost" size="small" onClick={() => setRevealed(true)}>
          {`Show ${hidden.length} earlier version${hidden.length === 1 ? "" : "s"}`}
        </Button>
      )}
    </div>
  );
}
