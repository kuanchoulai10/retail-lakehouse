const NAMESPACE_SEPARATOR = "\u001f";
const ENCODED_SEPARATOR = "%1F";

function segment(name: string): string {
  return encodeURIComponent(name);
}

export function apiNamespace(namespace: string[]): string {
  return namespace.map(segment).join(ENCODED_SEPARATOR);
}

export function namespaceFromParam(param: string): string[] {
  return param.split(NAMESPACE_SEPARATOR);
}

export function catalogPath(catalog: string): string {
  return `/catalogs/${segment(catalog)}`;
}

export function namespacePath(catalog: string, namespace: string[]): string {
  return `${catalogPath(catalog)}/namespaces/${apiNamespace(namespace)}`;
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
