# 7. One-time secrets are issued by a Gateway

Date: 2026-11-07

Status: Accepted

## Context

Some external systems return a secret only once. Polaris `createPrincipal` returns the client secret in its response. `rotateCredentials` returns a new one. A later read never returns the secret again.

If the secret were part of an aggregate, or returned by a Repository method, it could be persisted, cached, logged or returned by a later load. A repository is expected to give back the same state on every load, and a one-time secret does not.

Other systems do the same. AWS `CreateAccessKey`, GCP service-account keys and Stripe API keys each issue a secret as its own operation and never return it from a later read.

No code implements this ADR yet; the catalog and access contexts come in a later project.

## Considered options

1. Return the secret from a Repository method such as `add` or `save`.
2. Store the secret in the aggregate so later reads can show it.
3. Issue the secret through a Gateway. It is not part of aggregate state, and it travels only in the use case output.

## Decision

Option 3. An operation that returns a secret once is a Gateway, not a Repository method.

- Ports: `CreatePrincipalGateway` creates a principal. `UpdatePrincipalCredentialsGateway` rotates or resets its credentials. `Create` is in the gateway verb vocabulary for this purpose.
- The secret is never part of aggregate state. It is never persisted or logged.
- The secret travels in the use case output as a value object, `IssuedPrincipalCredentials`. Its `repr` redacts the value.
- The web response that carries the secret has `Cache-Control: no-store`.
- The UI shows the secret once. If the user loses it, rotate is the recovery path.

## Consequences

- No read path can return a secret, because none is stored.
- A lost secret cannot be recovered. The user rotates it.
- Callers handle a secret-bearing output with care. The redacting `repr` reduces accidental logging, but it does not replace care.
- Creating a principal is a Gateway call, and the aggregate is then loaded through `PrincipalsRepo`.
