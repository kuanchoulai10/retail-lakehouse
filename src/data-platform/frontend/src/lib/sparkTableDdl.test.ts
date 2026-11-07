import { describe, expect, it } from "vitest";
import { catalogTableFixture } from "../test/catalogApiStub";
import { sparkColumnType } from "./sparkColumnType";
import { sparkTableDdl } from "./sparkTableDdl";

describe("sparkColumnType", () => {
  it.each([
    ["boolean", "BOOLEAN"],
    ["int", "INT"],
    ["long", "BIGINT"],
    ["float", "FLOAT"],
    ["double", "DOUBLE"],
    ["decimal(10,2)", "DECIMAL(10,2)"],
    ["date", "DATE"],
    ["timestamp", "TIMESTAMP_NTZ"],
    ["timestamptz", "TIMESTAMP"],
    ["string", "STRING"],
    ["uuid", "STRING"],
    ["fixed[16]", "BINARY"],
    ["binary", "BINARY"],
  ])("maps the primitive %s to %s", (iceberg, spark) => {
    expect(sparkColumnType(iceberg)).toBe(spark);
  });

  it("translates required in a struct to NOT NULL", () => {
    expect(sparkColumnType("struct<city: required string, zip: string>")).toBe(
      "STRUCT<`city`: STRING NOT NULL, `zip`: STRING>",
    );
  });

  it("turns list into ARRAY and drops required, which Spark DDL cannot say for elements", () => {
    expect(sparkColumnType("list<required int>")).toBe("ARRAY<INT>");
  });

  it("translates nested maps and lists", () => {
    expect(sparkColumnType("map<string, list<required struct<a: long>>>")).toBe(
      "MAP<STRING, ARRAY<STRUCT<`a`: BIGINT>>>",
    );
  });

  it("quotes a struct field name that holds a backtick", () => {
    expect(sparkColumnType("struct<we`ird: int>")).toBe("STRUCT<`we``ird`: INT>");
  });
});

describe("sparkTableDdl", () => {
  it("builds create table with partitioning, location, properties and sort order, minus reserved keys", () => {
    expect(sparkTableDdl(catalogTableFixture())).toBe(
      [
        "CREATE TABLE `iceberg`.`retail`.`orders` (",
        "  `id` BIGINT NOT NULL,",
        "  `placed_at` TIMESTAMP COMMENT 'order time',",
        "  `address` STRUCT<`city`: STRING NOT NULL, `zip`: STRING>",
        ")",
        "USING iceberg",
        "PARTITIONED BY (days(`placed_at`))",
        "LOCATION 's3://warehouse/retail/orders'",
        "TBLPROPERTIES (",
        "  'format-version' = '2',",
        "  'write.format.default' = 'parquet'",
        ");",
        "",
        "ALTER TABLE `iceberg`.`retail`.`orders` WRITE ORDERED BY `id` ASC NULLS FIRST;",
      ].join("\n"),
    );
  });

  it("maps every partition transform", () => {
    const table = catalogTableFixture({
      partition_spec: {
        spec_id: 1,
        fields: [
          { source_id: 1, field_id: 1000, name: "a", transform: "identity" },
          { source_id: 1, field_id: 1001, name: "b", transform: "bucket[16]" },
          { source_id: 1, field_id: 1002, name: "c", transform: "truncate[4]" },
          { source_id: 2, field_id: 1003, name: "d", transform: "year" },
          { source_id: 2, field_id: 1004, name: "e", transform: "month" },
          { source_id: 2, field_id: 1005, name: "f", transform: "hour" },
          { source_id: 2, field_id: 1006, name: "g", transform: "void" },
        ],
      },
      sort_order: { order_id: 0, fields: [] },
    });
    const ddl = sparkTableDdl(table);
    expect(ddl).toContain(
      "PARTITIONED BY (`id`, bucket(16, `id`), truncate(4, `id`), years(`placed_at`), " +
        "months(`placed_at`), hours(`placed_at`))",
    );
    expect(ddl).not.toContain("ALTER TABLE");
  });

  it("escapes quotes in properties and keeps a format-version the table sets", () => {
    const table = catalogTableFixture({
      partition_spec: { spec_id: 0, fields: [] },
      properties: { "format-version": "3", note: "it's" },
    });
    const ddl = sparkTableDdl(table);
    expect(ddl).not.toContain("PARTITIONED BY");
    expect(ddl).toContain("'format-version' = '3'");
    expect(ddl).toContain("'note' = 'it''s'");
  });

  it("states the comment property as a COMMENT clause after USING iceberg", () => {
    const table = catalogTableFixture({
      partition_spec: { spec_id: 0, fields: [] },
      sort_order: { order_id: 0, fields: [] },
      properties: { comment: "the orders, it's all here" },
    });
    expect(sparkTableDdl(table)).toContain(
      ["USING iceberg", "COMMENT 'the orders, it''s all here'", "LOCATION"].join("\n"),
    );
    expect(sparkTableDdl(table)).not.toContain("'comment' =");
  });

  it("skips a void sort field instead of sorting by the bare column", () => {
    const table = catalogTableFixture({
      sort_order: {
        order_id: 2,
        fields: [
          { source_id: 1, transform: "void", direction: "asc", null_order: "nulls-first" },
          { source_id: 2, transform: "day", direction: "desc", null_order: "nulls-last" },
        ],
      },
    });
    expect(sparkTableDdl(table)).toContain("WRITE ORDERED BY days(`placed_at`) DESC NULLS LAST;");
  });

  it("writes no sort statement when every sort field is void", () => {
    const table = catalogTableFixture({
      sort_order: {
        order_id: 2,
        fields: [{ source_id: 1, transform: "void", direction: "asc", null_order: "nulls-first" }],
      },
    });
    expect(sparkTableDdl(table)).not.toContain("ALTER TABLE");
  });
});
