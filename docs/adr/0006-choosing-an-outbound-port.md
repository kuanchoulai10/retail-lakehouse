# 6. Choosing an outbound port: Repository, Store or Gateway

Date: 2026-11-07

Status: Accepted

## Context

The backend has three outbound port base classes: `Repository`, `Store` and `Gateway`. The naming convention says what each is called, but not how to choose between them. This matters now that some aggregates will have an external system of record. For example, a Polaris principal is our aggregate, but Polaris holds its data.

If the port is chosen by where the data lives, these aggregates would become gateways, and the domain model would lose its repository.

No code implements this ADR yet; the catalog and access contexts come in a later project.

## Considered options

1. Choose by where the data lives: our database means Repository, an external system means Gateway.
2. Choose by whether the thing is one of our aggregates.

## Decision

Option 2. The port follows what the thing is, not where its data lives.

- **Repository.** The thing is one of our aggregates. The port is `{Aggregate}Repo`, even when the system of record is external. The adapter is named after the technology. For example, the principal aggregate has the port `PrincipalsRepo` and the adapter `PrincipalsPolarisRepo`.
- **Store.** The data is ours and is not an aggregate. For example, the event outbox: `EventOutboxStore`.
- **Gateway.** We ask an external system to do or tell something, and this is not loading or saving one of our aggregates. For example, `SubmitJobRunGateway`.

## Consequences

- The domain model keeps one repository per aggregate, whichever system holds the data.
- Swapping the system of record changes the adapter, not the port.
- Operations that do not fit loading or saving an aggregate need a Gateway. ADR 0007 covers one such case, one-time secrets.
