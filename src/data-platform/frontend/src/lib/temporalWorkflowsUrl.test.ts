import { describe, expect, it } from "vitest";
import { temporalWorkflowsUrl } from "./temporalWorkflowsUrl";

describe("temporalWorkflowsUrl", () => {
  it("lists the running workflows tagged with the table uuid in the Temporal UI", () => {
    const uuid = "1f0e5c2a-8b7d-4e3f-9a6b-0c1d2e3f4a5b";
    expect(temporalWorkflowsUrl(uuid)).toBe(
      "/temporal/namespaces/default/workflows?query=" +
        encodeURIComponent(`TableUuid = "${uuid}" AND ExecutionStatus = "Running"`),
    );
  });
});
