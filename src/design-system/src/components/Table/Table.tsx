import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type TableProps = ComponentProps<"table">;
export type TableHeaderProps = ComponentProps<"thead">;
export type TableBodyProps = ComponentProps<"tbody">;
export type TableRowProps = ComponentProps<"tr">;
export type TableHeadProps = ComponentProps<"th"> & { numeric?: boolean };
export type TableCellProps = ComponentProps<"td"> & { numeric?: boolean };

export const Table = forwardRef<HTMLTableElement, TableProps>(({ className, ...rest }, ref) => (
  <table
    ref={ref}
    className={cn("type-body-medium w-full border-collapse text-on-surface", className)}
    {...rest}
  />
));
Table.displayName = "Table";

export const TableHeader = forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  (props, ref) => <thead ref={ref} {...props} />,
);
TableHeader.displayName = "TableHeader";

export const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>((props, ref) => (
  <tbody ref={ref} {...props} />
));
TableBody.displayName = "TableBody";

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, ...rest }, ref) => (
    <tr ref={ref} className={cn("border-b border-outline-dim", className)} {...rest} />
  ),
);
TableRow.displayName = "TableRow";

export const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ numeric = false, className, ...rest }, ref) => (
    <th
      ref={ref}
      className={cn(
        "type-label-large h-control px-3 py-1 font-semibold whitespace-nowrap",
        numeric ? "text-right tabular-nums" : "text-left",
        className,
      )}
      {...rest}
    />
  ),
);
TableHead.displayName = "TableHead";

export const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ numeric = false, className, ...rest }, ref) => (
    <td
      ref={ref}
      className={cn(
        "h-control px-3 py-1",
        numeric ? "text-right tabular-nums" : "text-left",
        className,
      )}
      {...rest}
    />
  ),
);
TableCell.displayName = "TableCell";
