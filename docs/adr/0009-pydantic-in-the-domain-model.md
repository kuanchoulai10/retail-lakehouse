# 9. Pydantic in the domain model

Date: 2026-11-10

Status: Accepted

## Context

The domain model was built on frozen and plain dataclasses, with a rule that the domain depends on nothing except `base` and the standard library. Every invariant is checked by hand in `__post_init__`, and every aggregate has hand-written converters to and from dicts and JSON. Both are code we maintain without adding value, and they have to be kept strict by hand (no `true` for an integer, no unknown keys).

The owner decided on 2026-11-09 to move the domain model to Pydantic v2. This reverses the earlier "no Pydantic" rule.

## Decision

The domain and `base` may import the standard library, `base`, their own context's domain, and `pydantic`, with `pydantic_core` and `annotated_types` (Pydantic's public types are built from them). Nothing else third-party.

- **Allow-list, not deny-list.** `tests/architecture/test_domain_dependencies.py` parses every file under `base/` and `context/*/application/domain/` and rejects any other import, so a newly added package is refused by default. Contract `domain-pure` still forbids the project's outer rings and the known frameworks.
- **Services stay free of Pydantic.** Contract `application-outer-rings-pydantic-free` forbids `pydantic` in `service`, `port` and `exceptions`. It allows indirect imports, because services reach Pydantic only through the domain.
- **Strict by default.** `ValueObject` and `DomainEvent` are frozen, strict and forbid extra keys. `Entity` and `AggregateRoot` are strict, forbid extra keys and validate assignment.
- **Construction errors are Pydantic's.** A broken invariant raises `ValidationError` and the API answers 422. Transition errors (`InvalidTableTransition`, `InvalidRunTransition`) stay and answer 409.
- **External formats do not change.** REST bodies, the settings JSON in PostgreSQL, Temporal payloads and the Spark request stay byte-for-byte the same; durations are integer seconds on the wire and `timedelta` in the domain.

The full design is in `docs/superpowers/specs/2026-11-10-pydantic-domain-model-design.md`.

## Consequences

- Invariants and converters become declarations and `model_validate` / `model_dump`, so there is less hand-written code to keep correct.
- The domain now depends on a third-party library. The allow-list keeps that dependency to Pydantic alone.
- `model_copy` does not validate, so domain code derives a changed copy through one helper that does, and an architecture test forbids bare `model_copy`.
- Annotations that were `TYPE_CHECKING`-only may have to become runtime imports, so import cycles are checked by architecture tests (`tests/architecture/test_domain_models_complete.py`).
- Adapters that hand a `list` to a `tuple` field, or a plain string to an enum field, now fail under strict mode at runtime.
