import { describe, expect, it } from "vitest";
import type { SchemaFieldComparisonApiResponse } from "@/api/generated/model";
import { schemaDiffItems } from "./schemaDiffItems";

function field(overrides: Partial<SchemaFieldComparisonApiResponse>): SchemaFieldComparisonApiResponse {
  return {
    field_id: 1,
    depth: 0,
    path: ["order_id"],
    previous_path: ["order_id"],
    type: "long",
    previous_type: "long",
    required: true,
    previous_required: true,
    doc: null,
    previous_doc: null,
    changes: [],
    ...overrides,
  };
}

function items(...fields: SchemaFieldComparisonApiResponse[]) {
  return schemaDiffItems({ schema_id: 2, base_schema_id: 1, fields });
}

describe("schemaDiffItems", () => {
  it("gives a renamed and promoted field one changed row", () => {
    expect(
      items(
        field({
          field_id: 2,
          path: ["customer"],
          previous_path: ["customer_id"],
          type: "long",
          previous_type: "int",
          required: false,
          previous_required: false,
          changes: ["renamed", "type_changed"],
        }),
      ),
    ).toEqual([
      {
        id: "2",
        change: "changed",
        label: "customer",
        depth: 0,
        tags: ["Renamed", "Type changed"],
        before: "int · optional",
        after: "long · optional",
        description: "Renamed from customer_id",
      },
    ]);
  });

  it("gives a removed nested field its full path and no after", () => {
    const [item] = items(
      field({
        field_id: 9,
        depth: 1,
        path: null,
        previous_path: ["shipping", "zip"],
        type: null,
        required: null,
        previous_type: "string",
        previous_required: false,
        changes: ["removed"],
      }),
    );
    expect(item).toMatchObject({ id: "9", change: "removed", label: "shipping.zip", depth: 1, before: "string · optional" });
    expect(item?.after).toBeUndefined();
  });

  it("gives an added field only its after", () => {
    const [item] = items(
      field({ field_id: 7, path: ["coupon"], previous_path: null, type: "string", required: false, previous_type: null, previous_required: null, changes: ["added"], doc: "Code entered at checkout" }),
    );
    expect(item).toMatchObject({ change: "added", label: "coupon", after: "string · optional", description: "Code entered at checkout" });
    expect(item?.before).toBeUndefined();
  });

  it("shows a nullability change as before and after, without a tag for added or removed", () => {
    const [item] = items(field({ required: false, previous_required: true, changes: ["nullability_changed"] }));
    expect(item).toMatchObject({
      change: "changed",
      tags: ["Nullability changed"],
      before: "long · required",
      after: "long · optional",
    });
  });

  it("describes a doc change and keeps an unchanged field's before empty", () => {
    const [changed, unchanged] = items(
      field({ doc: "Order key", previous_doc: null, changes: ["doc_changed"] }),
      field({ field_id: 3, path: ["amount"], previous_path: ["amount"], doc: "Gross", previous_doc: "Gross" }),
    );
    expect(changed).toMatchObject({ tags: ["Doc changed"], description: "Doc: none → Order key" });
    expect(changed?.before).toBeUndefined();
    expect(unchanged).toMatchObject({ change: "unchanged", description: "Gross", tags: [] });
  });

  it("joins a rename and a doc change in one description", () => {
    const [item] = items(
      field({ path: ["a"], previous_path: ["b"], doc: null, previous_doc: "old", changes: ["renamed", "doc_changed"] }),
    );
    expect(item?.description).toBe("Renamed from b · Doc: old → none");
  });
});
