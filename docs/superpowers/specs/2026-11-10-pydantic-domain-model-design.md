# Pydantic Domain Model Design

The backend domain model moves from dataclasses to Pydantic v2 models. **The goal is one definition per concept**: a value object's fields, defaults, constraints and external shape are declared once on the class, and the hand-written converters that repeat them (`maintenance_settings_from_dict`, `maintenance_settings_to_dict`, `MaintenanceSettingsCodec`, the catalog `*_config_from_dict` / `*_config_to_dict`) collapse into `model_validate` and `model_dump`. This reverses the rule "Domain depends on nothing except `base/` and stdlib. No Pydantic" (owner's call, 2026-11-09, `docs/agents/known-follow-ups.md`).

## Decisions

| Topic | Decision | Source |
|---|---|---|
| What moves | `ValueObject`, `EntityId`, `Entity`, `AggregateRoot`, `DomainEvent` and every domain class built on them, in both bounded contexts (`catalog`, `table_maintenance`) | owner |
| Hand-written converters | Replaced in this initiative by `model_validate` / `model_dump` | owner |
| Construction errors | A broken invariant at construction raises Pydantic's `ValidationError`. Construction-only exceptions (`InvalidMaintenanceSettings`, `InvalidTableDiscoveryRule`, `InvalidReconciliation`) are deleted once nothing raises them outside a validator. The API still answers 422, with a one-line message built from the first error. | owner |
| Transition errors | Exceptions raised by aggregate methods for a forbidden state change (`InvalidTableTransition`, `InvalidRunTransition`) stay, and still map to 409 | owner |
| Assignment | Aggregates validate every assignment (`validate_assignment=True`). Cross-field rules are still checked in the method before it assigns, as today. | owner |
| Allowed dependencies | Domain and `base` may import the stdlib, `base`, their own context's domain, and `pydantic` (with `pydantic_core` and `annotated_types`, which Pydantic's public types are built from). Nothing else third-party. Enforced as an allow-list, not the current deny-list, so a newly added package is rejected by default. | owner |

## External formats do not change

**Every format that leaves the process stays byte-for-byte compatible**: the REST API bodies, the settings JSON stored in PostgreSQL (rows already exist), Temporal workflow and activity payloads, and the Spark application arguments. Durations are integer seconds on the wire (`min_interval_seconds`) and `timedelta` in the domain (`min_interval`); a non-whole-second duration is still rejected when encoded. Enums travel as their string values. The plan proves compatibility with round-trip tests against today's encoders before deleting them.

## Base types

- `ValueObject`: `BaseModel`, `frozen=True`, `strict=True`, `extra="forbid"`. Equality and hashing by value come from Pydantic.
- `EntityId`: a `RootModel[str]`, frozen and strict, so `TableId("abc")` keeps working positionally and the ~270 call sites stay as they are. `OrderId("1") != UserId("1")` still holds. `str(id)` returns the raw value.
- `Entity`: `BaseModel`, `strict=True`, `extra="forbid"`, `validate_assignment=True`; keeps identity equality and hashing by `id`.
- `AggregateRoot`: an `Entity` whose pending events are a Pydantic private attribute, so they are never serialized or compared.
- `DomainEvent`: `BaseModel`, frozen and strict, with `occurred_at` defaulting to now in UTC.
- The inheritance-depth guard (`enforce_max_depth` in `__init_subclass__`) keeps working with Pydantic's metaclass.
- `Repository`, `UseCase`, `Gateway`, `Store`, `EventHandler`, `EventDispatcher` are interfaces and do not change.

## Behaviour that must survive

- **Copying with a change re-validates.** `dataclasses.replace` validated through `__post_init__`; Pydantic's `model_copy(update=…)` does not. Domain code that derives a changed copy goes through one helper that validates, never through bare `model_copy`.
- **Strictness.** Today's converters reject a boolean where an integer is expected and reject unknown keys. Strict mode and `extra="forbid"` keep both.
- **Error translation.** `translate_domain_errors` keeps mapping transition errors to `ConflictError` and every other `ValueError`, Pydantic's included, to `ValidationError`.

## Out of scope

Port DTOs (`*UseCaseInput` / `*UseCaseOutput`), Temporal contracts, web DTOs (already Pydantic, and kept separate from the domain), and `StrEnum`s stay as they are. Kafka or outbox publishing of domain events is a later step this enables, not part of this work.

## Left to the builder

The order of migration across files, how the external seconds format is expressed (a reusable annotated type in `base` or per-field serializers), the exact helper name for validated copies, and how the 422 message is extracted from a Pydantic error.
