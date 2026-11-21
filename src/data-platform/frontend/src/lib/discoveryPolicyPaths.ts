// The console's discovery policy pages: the list, one policy's edit page, and a kept version.

export function discoveryPoliciesPath(): string {
  return "/discovery-policies";
}

export function discoveryPolicyPath(name: string): string {
  return `${discoveryPoliciesPath()}/${encodeURIComponent(name)}`;
}

export function discoveryPolicyVersionPath(name: string, version: number): string {
  return `${discoveryPolicyPath(name)}/versions/${version}`;
}
