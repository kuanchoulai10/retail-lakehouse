const NAMESPACE_SEPARATOR = "\u001f";

function segment(name: string): string {
  return encodeURIComponent(name);
}

// A namespace as one path segment or query value: its parts joined by U+001F. The generated
// API client encodes it (U+001F goes out as %1F), so pass it unencoded.
export function apiNamespace(namespace: string[]): string {
  return namespace.join(NAMESPACE_SEPARATOR);
}

export function namespaceFromParam(param: string): string[] {
  return param.split(NAMESPACE_SEPARATOR);
}

export function catalogsPath(): string {
  return "/catalogs";
}

export function catalogPath(catalog: string): string {
  return `${catalogsPath()}/${segment(catalog)}`;
}

export function namespacePath(catalog: string, namespace: string[]): string {
  return `${catalogPath(catalog)}/namespaces/${segment(apiNamespace(namespace))}`;
}

export function tablePath(catalog: string, namespace: string[], table: string, tab?: string): string {
  const base = `${namespacePath(catalog, namespace)}/tables/${segment(table)}`;
  return tab === undefined ? base : `${base}/${segment(tab)}`;
}

export function viewPath(catalog: string, namespace: string[], view: string): string {
  return `${namespacePath(catalog, namespace)}/views/${segment(view)}`;
}

export function genericTablePath(catalog: string, namespace: string[], name: string): string {
  return `${namespacePath(catalog, namespace)}/generic-tables/${segment(name)}`;
}
