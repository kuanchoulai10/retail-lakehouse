import { describe, expect, it } from "vitest";
import { writerLabel } from "./writerLabel";

describe("writerLabel", () => {
  it("names the known writers", () => {
    expect(writerLabel("kafka_connect")).toBe("Kafka Connect");
    expect(writerLabel("spark")).toBe("Spark");
    expect(writerLabel("unknown")).toBe("Unknown");
  });

  it("passes an unexpected writer through", () => {
    expect(writerLabel("flink")).toBe("flink");
  });
});
