import { EmptyState, TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";
import { namespacePath } from "@/lib/catalogPaths";

interface Props {
  objectKind: string;
  catalog: string;
  namespace: string[];
  name: string;
}

// A link (from the maintenance list, a bookmark) can name an object the catalog no longer
// holds under that name; the namespace page shows what it holds now.
export function CatalogObjectNotFound({ objectKind, catalog, namespace, name }: Props) {
  const where = [catalog, ...namespace].join(" / ");
  return (
    <EmptyState
      role="status"
      className="rounded-lg border border-outline"
      title={
        <>
          The {objectKind} <span className="font-mono">{name}</span> is not in the catalog
        </>
      }
      description={
        <>
          It may have been renamed or dropped.{" "}
          <TextLink asChild inline>
            <Link to={namespacePath(catalog, namespace)}>
              Go to {where}
            </Link>
          </TextLink>
        </>
      }
    />
  );
}
