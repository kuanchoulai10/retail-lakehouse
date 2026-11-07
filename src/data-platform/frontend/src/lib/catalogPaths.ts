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

export function catalogsPath(): string {
  return "/catalogs";
}

export function catalogPath(catalog: string): string {
  return `${catalogsPath()}/${segment(catalog)}`;
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

// Paths of our catalog API, relative to the API prefix that apiGet and apiSend add.

export function catalogsApiPath(): string {
  return "/v1/catalogs";
}

export function catalogApiPath(catalog: string): string {
  return `${catalogsApiPath()}/${segment(catalog)}`;
}

export function namespacesApiPath(catalog: string, parent: string[]): string {
  const base = `${catalogApiPath(catalog)}/namespaces`;
  return parent.length === 0 ? base : `${base}?parent=${apiNamespace(parent)}`;
}

export function namespaceApiPath(catalog: string, namespace: string[]): string {
  return `${catalogApiPath(catalog)}/namespaces/${apiNamespace(namespace)}`;
}

export function namespacePropertiesApiPath(catalog: string, namespace: string[]): string {
  return `${namespaceApiPath(catalog, namespace)}/properties`;
}

export function tablesApiPath(catalog: string, namespace: string[]): string {
  return `${namespaceApiPath(catalog, namespace)}/tables`;
}

export function tableApiPath(catalog: string, namespace: string[], table: string): string {
  return `${tablesApiPath(catalog, namespace)}/${segment(table)}`;
}

export function tableRenameApiPath(catalog: string, namespace: string[], table: string): string {
  return `${tableApiPath(catalog, namespace, table)}/rename`;
}

export function tablePropertiesApiPath(catalog: string, namespace: string[], table: string): string {
  return `${tableApiPath(catalog, namespace, table)}/properties`;
}

export function viewsApiPath(catalog: string, namespace: string[]): string {
  return `${namespaceApiPath(catalog, namespace)}/views`;
}

export function viewApiPath(catalog: string, namespace: string[], view: string): string {
  return `${viewsApiPath(catalog, namespace)}/${segment(view)}`;
}

export function genericTablesApiPath(catalog: string, namespace: string[]): string {
  return `${namespaceApiPath(catalog, namespace)}/generic-tables`;
}

export function genericTableApiPath(catalog: string, namespace: string[], name: string): string {
  return `${genericTablesApiPath(catalog, namespace)}/${segment(name)}`;
}
