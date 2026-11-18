# 10. Pydantic in inbound ports

Date: 2026-11-18

Status: Accepted. Partly supersedes ADR 0009 ("Services stay free of Pydantic").

## Context

Each inbound port (a use case) takes an input and returns an output. Both were frozen dataclasses, and a dataclass checks nothing: a web router, a Temporal activity and the Kafka event consumer each build the same input from what they received, and each had to get the types right itself. A Temporal activity gets a dict of JSON primitives and converts ISO strings to `datetime` and lists to tuples by hand; an `asdict` pass turns an output back into a dict. A wrong type reaches the service and fails there, or not at all.

Tom Hombergs ("Get Your Hands Dirty on Clean Architecture", which this backend follows) puts validation in the input model: the input checks itself when it is built, so a use case never sees an invalid request, whichever adapter built it. ADR 0009 moved the domain to Pydantic v2 and kept services, ports and exceptions free of it. The owner decided on 2026-11-18 (Linear KCL-88) to give inbound ports the same self-validating models.

## Considered options

1. Keep dataclasses and validate in each entry point. Three copies of the same checks, and nothing stops a fourth entry point from skipping them.
2. Validate in each service. The service then works with half-trusted data, and every service repeats the type checks the input already declares.
3. Make the inputs and outputs Pydantic models on two `base` building blocks. One validation path for every entry point.

Option 3 uses `BaseModel` subclasses, not `pydantic.dataclasses` or dataclasses validated through a `TypeAdapter`: the `InvariantViolation` guard, the inheritance-depth rule and `from_primitives` live on a `BaseModel` base, and one model type for the domain and the ports avoids two validation behaviours.

## Decision

Option 3.

- **Two building blocks.** Every inbound port's input extends `base.UseCaseInput` and its output `base.UseCaseOutput`. Both are frozen, strict (`"1"` is not an `int`, a `list` is not a `tuple`) and forbid unknown keys. A refused construction raises `InvariantViolation`, as the model bases do (ADR 0009, note of 2026-11-18); assigning to a field raises `AttributeError`.
- **One validation path.** Code builds an input by keyword. An entry point that holds a dict of JSON primitives (a Temporal activity, the event consumer) builds it with `UseCaseInput.from_primitives(data)`, which validates in strict JSON mode: an ISO string becomes a `datetime`, an array a `tuple`. A web router builds it by keyword from what FastAPI parsed.
- **`from_primitives` is a tolerant reader: unknown keys are ignored, missing or mistyped keys are refused; construction in code stays strict.** It validates with `extra="ignore"` at every depth, nested classes included, while keyword construction, `model_validate` and `model_validate_json` still forbid extra keys, so a typo in code fails. The reason is the rolling deploy: a newer workflow can send a key an older worker pod does not know yet, and refusing it is non-retryable, which for the plan activity would silently drop a user's manual trigger. Before the migration the activities picked keys by hand and ignored the rest; the tolerant reader keeps that. This follows Martin Fowler's Tolerant Reader (https://martinfowler.com/bliki/TolerantReader.html): read only what you need, ignore the rest. `ValueObject.from_primitives`, which reads persisted JSON, stays strict.
- **Primitives only.** Fields hold `str`, `int`, `float`, `bool`, `None`, `datetime`, `timedelta`, `list`, `tuple`, `dict`, and classes nested one level inside the input or output, named by what they hold (`ListTableCommitsUseCaseOutput.Commit`) and extending the same base. Never a domain type: adapters still never see the domain. Each `input.py` / `output.py` defines exactly one top-level class, and a use case's `__init__.py` exports exactly its use case, input and output.
- **Services still never import Pydantic.** Ports reach Pydantic only through `base`, and services only through ports and the domain. Contract `application-outer-rings-pydantic-free` is unchanged: `service`, `port` and `exceptions` never import `pydantic` directly, and it allows indirect imports.
- **External formats do not change.** REST bodies, Temporal payloads and the settings JSON stay the same. `activity_payload` dumps a `UseCaseOutput` with `model_dump()` and writes datetimes with `isoformat()`, exactly as it wrote a dataclass. A `float` field always serialises as a float (`1.0`), even when it was set from an int, where a dataclass passed the int through (`1`).
- **An input that cannot be built is a client error at every edge.** A web router, a Temporal activity or the event consumer that builds a port input, or runs a use case, and gets `InvariantViolation` treats it exactly like the application `ValidationError`: the web edge answers 422 with `{"detail": <its one line>}` through the same handler, a Temporal activity fails at once with a non-retryable `ApplicationError` of type `InvariantViolation`, and the event consumer drops the hint without retry (a hint input it cannot build is skipped as a malformed event).
- **Every use case is checked.** `tests/architecture/test_inbound_port_models.py` checks each use case under `port/inbound`, with no list of exceptions, and `tests/architecture/test_inbound_port_field_names.py` checks the field names.

## Consequences

- An invalid request fails where it is built, with the same one-line `InvariantViolation` text for every entry point.
- Strict mode means callers pass the declared types: a service builds an output with a `tuple` for a `tuple` field, and a router converts a query list to a tuple.
- A router that builds an input with refused data raises `InvariantViolation` in the web adapter, outside any service's error translation; each context's web error handlers map it to 422 like `ValidationError`, so it never surfaces as a 500. The same holds for Temporal (non-retryable) and the event consumer (dropped without retry).
- Ports now depend on Pydantic, through `base`. The dependency stays in one place, the two building blocks, which ruff treats as runtime-evaluated bases so field types stay imported at runtime.
