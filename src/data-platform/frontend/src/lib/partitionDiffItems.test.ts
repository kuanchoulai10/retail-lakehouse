import { describe, expect, it } from "vitest";
import type { PartitionFieldComparisonApiResponse } from "@/api/generated/model";
import { partitionDiffItems } from "./partitionDiffItems";

function field(overrides: Partial<PartitionFieldComparisonApiResponse>): PartitionFieldComparisonApiResponse {
  return {
    field_id: 1000,
    previous_field_id: 1000,
    name: "order_ts_day",
    previous_name: "order_ts_day",
    transform: "day",
    previous_transform: "day",
    expression: "day(order_ts)",
    previous_expression: "day(order_ts)",
    source_path: ["order_ts"],
    previous_source_path: ["order_ts"],
    changes: [],
    ...overrides,
  };
}

function items(...fields: PartitionFieldComparisonApiResponse[]) {
  return partitionDiffItems({ spec_id: 1, base_spec_id: 0, fields });
}

describe("partitionDiffItems", () => {
  it("writes a transform change as before and after, under the new field id", () => {
    expect(
      items(
        field({
          field_id: 1001,
          previous_field_id: 1000,
          name: "order_ts_hour",
          previous_name: "order_ts_day",
          transform: "hour",
          previous_transform: "day",
          expression: "hour(order_ts)",
          previous_expression: "day(order_ts)",
          changes: ["transform_changed"],
        }),
      ),
    ).toEqual([
      {
        id: "1001",
        change: "changed",
        label: "order_ts_hour",
        tags: ["Transform changed"],
        before: "day(order_ts)",
        after: "hour(order_ts)",
      },
    ]);
  });

  it("gives a removed field its previous id, name and expression", () => {
    const [item] = items(
      field({ field_id: null, name: null, transform: null, expression: null, source_path: null, changes: ["removed"] }),
    );
    expect(item).toMatchObject({ id: "1000", change: "removed", label: "order_ts_day", before: "day(order_ts)" });
    expect(item?.after).toBeUndefined();
  });

  it("gives an added field only its after", () => {
    const [item] = items(
      field({ previous_field_id: null, previous_name: null, previous_transform: null, previous_expression: null, previous_source_path: null, changes: ["added"] }),
    );
    expect(item).toMatchObject({ change: "added", after: "day(order_ts)" });
    expect(item?.before).toBeUndefined();
  });

  it("says where a renamed field came from and leaves an unchanged one plain", () => {
    const [renamed, unchanged] = items(
      field({ name: "day_of_order", changes: ["renamed"] }),
      field({ field_id: 1002, previous_field_id: 1002, name: "region", previous_name: "region", expression: "identity(region)", previous_expression: "identity(region)" }),
    );
    expect(renamed).toMatchObject({ tags: ["Renamed"], description: "Renamed from order_ts_day", after: "day(order_ts)" });
    expect(renamed?.before).toBeUndefined();
    expect(unchanged).toMatchObject({ change: "unchanged", label: "region", after: "identity(region)" });
    expect(unchanged?.description).toBeUndefined();
  });
});
