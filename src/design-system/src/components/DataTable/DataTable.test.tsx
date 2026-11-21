import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createDataTableColumnHelper } from "./createDataTableColumnHelper";
import { DataTable } from "./DataTable";

type Row = { id: string; name: string };

const helper = createDataTableColumnHelper<Row>();
const columns = helper.columns([helper.accessor("name", { header: "Name", enableSorting: false })]);

describe("DataTable", () => {
  it("refuses rows that both expand and open", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <DataTable<Row>
          caption="Tables"
          columns={columns}
          data={[{ id: "1", name: "sales.orders" }]}
          renderDetail={() => null}
          onOpenRow={() => undefined}
        />,
      ),
    ).toThrow("expands");
  });
});
