import type { Crumb } from "@/components/Breadcrumbs";
import { catalogPath, catalogsPath, namespacePath } from "./catalogPaths";

// Catalogs / catalog / each namespace level / the object, every parent linked.
export function catalogObjectCrumbs(catalog: string, namespace: string[], name: string): Crumb[] {
  return [
    { label: "Catalogs", to: catalogsPath() },
    { label: catalog, to: catalogPath(catalog) },
    ...namespace.map((part, index) => ({ label: part, to: namespacePath(catalog, namespace.slice(0, index + 1)) })),
    { label: name },
  ];
}
