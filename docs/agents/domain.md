# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

If it doesn't exist, **proceed silently**. Don't flag its absence; don't suggest creating it upfront.

## File structure

```
/
├── docs/adr/
│   ├── 0001-single-table-aggregate.md
│   └── 0002-two-lifecycle-classes.md
└── src/
```

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
