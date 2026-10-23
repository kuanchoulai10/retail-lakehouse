# 4. Backslash escaping for Spark SQL string literals

Date: 2026-10-24

Status: Accepted

## Context

The control plane renders Iceberg procedure calls as Spark SQL text: table identifiers, `options` maps, and `rewrite_data_files` `where` clauses built from partition values. A partition value can contain a single quote or a backslash, for example `o'neil`. The `where` clause is itself a string literal inside the `CALL`, so a value is quoted twice.

Standard SQL (and Trino) escapes a quote by doubling it. Spark 4.0 with its default settings does not: an empirical check on `apache/spark:4.0.0` showed `'o''neil'` parses as `oneil` (two adjacent literals concatenated), while `'o\'neil'` parses as `o'neil` and `'a\b'` as `a` + `b` with the backslash consumed.

## Considered options

1. Double single quotes (standard SQL).
2. Escape with backslashes: first `\` to `\\`, then `'` to `\'`.
3. Avoid literals: pass values through DataFrame or procedure APIs instead of SQL text.

## Decision

Option 2. `build_partition_filters` (backend domain) renders string partition values with backslash escaping, and the Spark runtime (`sql_builder.sql_literal`) applies the same rule again when it embeds the `where` clause, table identifier and option values as literals in the `CALL`. Identifiers are backtick-quoted with doubled backticks. Timestamp values use `TIMESTAMP_NTZ '...'` for `timestamp` and `TIMESTAMP '...+00:00'` for `timestamptz`.

## Consequences

- Values with quotes and backslashes round-trip. The end-to-end check compacts a partition `region = 'o''neil'` (written by Trino with doubling) through a `where` clause rendered with backslashes, on real Spark.
- The rule depends on Spark's default `spark.sql.parser.escapedStringLiterals=false`. Changing that setting breaks the rendering, so the runtime must not set it.
- Trino SQL and Spark SQL now use different escaping. Code that writes SQL for both engines must not share a literal helper.
