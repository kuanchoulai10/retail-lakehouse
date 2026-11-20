import { useSearchParams } from "react-router";

// A version id in the url: a non-negative integer, anything else reads as no choice.
function parseId(value: string | null): number | undefined {
  return value !== null && /^\d+$/.test(value) ? Number(value) : undefined;
}

export type SchemaHistorySelection = {
  schemaId: number | undefined;
  baseSchemaId: number | undefined;
  schemaOnlyChanges: boolean;
  specId: number | undefined;
  baseSpecId: number | undefined;
  specOnlyChanges: boolean;
  setSchema: (id: number) => void;
  setBaseSchema: (id: number | undefined) => void;
  setSchemaOnlyChanges: (on: boolean) => void;
  setSpec: (id: number) => void;
  setBaseSpec: (id: number | undefined) => void;
  setSpecOnlyChanges: (on: boolean) => void;
};

// The Schema tab's choices, kept in the url so a comparison can be shared and survives a reload.
export function useSchemaHistorySelection(): SchemaHistorySelection {
  const [searchParams, setSearchParams] = useSearchParams();

  // A param set to its default (no id, switch off) leaves the url.
  const update = (changes: Record<string, string | undefined>) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value === undefined) next.delete(key);
          else next.set(key, value);
        }
        return next;
      },
      { replace: true },
    );

  return {
    schemaId: parseId(searchParams.get("schema")),
    baseSchemaId: parseId(searchParams.get("base")),
    schemaOnlyChanges: searchParams.get("only_changes") === "1",
    specId: parseId(searchParams.get("spec")),
    baseSpecId: parseId(searchParams.get("spec_base")),
    specOnlyChanges: searchParams.get("spec_only_changes") === "1",
    setSchema: (id) => update({ schema: String(id), base: undefined }),
    setBaseSchema: (id) => update({ base: id === undefined ? undefined : String(id) }),
    setSchemaOnlyChanges: (on) => update({ only_changes: on ? "1" : undefined }),
    setSpec: (id) => update({ spec: String(id), spec_base: undefined }),
    setBaseSpec: (id) => update({ spec_base: id === undefined ? undefined : String(id) }),
    setSpecOnlyChanges: (on) => update({ spec_only_changes: on ? "1" : undefined }),
  };
}
