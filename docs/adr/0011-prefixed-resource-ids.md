# 11. Prefixed resource ids

Date: 2026-11-19

Status: Accepted.

## Context

The table maintenance context mints most of its ids as bare UUIDs or as strings built from other values (a run id, a reconciliation id, a round id, a candidate id, an attachment id, a rule set id). A bare UUID in a log line, a URL or a database row does not say what it identifies, and nothing refuses a run id passed where a round id belongs. A maintenance policy has no id of its own: other aggregates point at it by name, so a rename would break every link to it, and the name has to serve as both display text and key. Linear KCL-73 asks for ids that say what they are, checked for that shape wherever they enter, and for a policy id so that a name is only for display and URLs.

Stripe-style prefixed ids and the TypeID specification (https://github.com/jetify-com/typeid) both put a short type prefix before a time-ordered UUID. TypeID writes the UUIDv7 as 26 lowercase Crockford base32 characters, which sort as text in time order and need no escaping in a URL.

Temporal workflows must mint some of these ids (a workflow starts a run and a round). A workflow runs in Temporal's sandbox and may import neither `base` nor Pydantic (contract `temporal-workflows-sandbox-safe`), and it must be deterministic, so it cannot call `uuid.uuid7()`; it can only use `workflow.now()` and `workflow.random()`. The domain mints the same ids through `base.EntityId`. Both need one encoder.

## Considered options

For the id format:

1. Keep bare UUIDs and rely on typed id classes. The type is gone once the id is a string in a log, a URL or a row, and a UUID of one kind passes for another.
2. Prefixed ids with a plain random suffix. Readable, but not ordered by time.
3. Prefixed ids with a UUIDv7 suffix in the TypeID encoding (this decision).

For where the encoder lives:

1. Put it in `base` and let workflows import it. Not possible: workflows may not import `base`, which depends on Pydantic.
2. Copy it into the Temporal contracts. Two encoders that must agree, with nothing but a test to keep them equal.
3. A small stdlib-only package both import. This is what the DDD literature calls a Shared Kernel (Evans, "Domain-Driven Design", ch. 14): a small part of the model that two parts agree to share and change together (this decision).

## Decision

- **Format.** `<prefix>-<suffix>`. The suffix is a UUIDv7 written as 26 lowercase Crockford base32 characters (alphabet `0123456789abcdefghjkmnpqrstvwxyz`), 128 bits big-endian, so the first character is `0` to `7`. This is exactly the TypeID suffix encoding: UUID `0188bac7-4afa-78aa-bc3b-bd1eef28d881` is `01h2xcejqtf2nbrexx3vqjhp41`. A prefix is 2 to 8 lowercase letters. The pattern for a prefix `p` is `^p-[0-7][0-9a-hjkmnp-tv-z]{25}$`.
- **Prefixes (table maintenance only).** `mp-` TableMaintenancePolicyId (new), `dp-` TableDiscoveryRulesId, `dr-` TableDiscoveryRuleId, `pa-` TableMaintenancePolicyAttachmentId, `mr-` TableMaintenanceRunId, `rc-` TableReconciliationId. `cr-` (CompactionRoundId) and `cc-` (CompactionCandidateId) were retired with their aggregates on 2026-11-20 and must not be reused.
- **Unchanged ids.** The table maintenance `TableId` stays the Iceberg table UUID, `CatalogDiscoveryId` stays the catalog name, and every id in the catalog context stays what Polaris gives (Polaris is its source of truth). The global discovery rules and the default maintenance policy have fixed ids, `dp-00000000000000000000000000` and `mp-00000000000000000000000000`.
- **Names for display and URLs only.** REST paths and console URLs keep using policy names. Every relation to a policy is by its `mp-` id.
- **`shared_kernel`.** A top-level package beside `base`, stdlib only, holding `prefixed_id_from_parts(prefix, unix_ms, random_bits)`, `new_prefixed_id(prefix)` and `prefixed_id_pattern(prefix)`. `base.EntityId` uses it to mint and check ids. Temporal contracts and workflows use `prefixed_id_from_parts(prefix, int(workflow.now().timestamp() * 1000), workflow.random().getrandbits(74))` to mint deterministic ids, so a replayed workflow reuses the same id. The package imports nothing from this project and nothing third-party; import-linter contract `shared-kernel-stdlib-only` and `tests/architecture/test_shared_kernel_stdlib_only.py` enforce it. Any package may import it, and it stays small.
- **No data migration.** Old rows are not converted. The cluster is rebuilt after the change, and an id of the old shape found in storage is refused when read.

## Consequences

- An id says what it is in a log line, a URL and a row, and a wrong kind is refused where it enters instead of failing later.
- Ids sort by creation time (to the millisecond) as text, which keeps index inserts mostly at the end and lets a list order by id.
- A stale link or bookmark carrying an old bare UUID is refused with a message naming the expected shape.
- The suffix is a time stamp plus random bits, so an id shows when its resource was created. These ids are not secrets.
- An attachment (`pa-`) and a compaction candidate (`cc-`, removed 2026-11-20) got random ids, not ids derived from their natural key. What made two of them the same thing (one attachment per target, one candidate per partition) could no longer come from the id, so it moves to unique constraints in the database.
- A new package means one more root package for import-linter, ruff's isort settings and the architecture tests. It ships in the image with `base`, because the Dockerfile copies the whole backend directory.
- The encoder is written once and tested against the TypeID specification's vector, so other TypeID tools read these ids.
