import type { CatalogTablePropertyApiResponse } from "@/api/generated/model";

// A reset deletes a property only when there is no default to write back: a custom key the
// catalog gives a default is reset to it, like any known key.
export function resetDeletesProperty(property: CatalogTablePropertyApiResponse): boolean {
  return property.custom && property.default_source === null;
}
