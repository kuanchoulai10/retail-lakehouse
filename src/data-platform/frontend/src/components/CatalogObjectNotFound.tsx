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
    <section role="status" className="flex flex-col gap-2 rounded-lg border border-border p-6 text-sm">
      <p className="font-medium">
        The {objectKind} <span className="font-mono text-[13px]">{name}</span> is not in the catalog
      </p>
      <p className="text-muted-foreground">
        It may have been renamed or dropped.{" "}
        <Link to={namespacePath(catalog, namespace)} className="underline hover:text-foreground">
          Go to {where}
        </Link>
      </p>
    </section>
  );
}
