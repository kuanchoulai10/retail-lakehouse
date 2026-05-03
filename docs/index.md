---
tags:
  - Apache Iceberg
  - Apache Kafka
  - Apache Polaris
  - Trino
  - Argo CD
  - OpenTelemetry
---
# Retail Lakehouse Platform

A self-hosted retail lakehouse that runs end-to-end on a single Mac, built to showcase three engineering disciplines side by side: Domain-Driven Design, streaming data infrastructure, and production-grade observability. Everything from the colima VM up to the Trino query engine is brought up by a single `task onboard` command.

## Highlights

=== "Software Engineering (DDD)"

    - **Strict Clean Architecture, enforced in CI.** `import-linter` blocks any dependency that crosses layers in the wrong direction (`adapter` to `application` to `domain`, no skipping).
    - **Single image, three roles.** The same container runs as API, Scheduler, or Outbox publisher depending on the `GLAC_COMPONENT` env var, following 12-factor.
    - **Full DDD building blocks.** `AggregateRoot`, `ValueObject`, `DomainEvent`, `Repository`, and `Gateway` paired with an explicit outbound port-adapter naming convention (`{Aggregate}{Tech}Repo`, `{Verb}{Noun}{Tech}Gateway`).

=== "Data Engineering"

    - **End-to-end CDC lakehouse.** MySQL to Debezium to Kafka to Iceberg sink, with exactly-once delivery and automatic schema evolution.
    - **Iceberg + Polaris + MinIO.** A fully self-hosted REST-catalog lakehouse with no cloud dependency; the entire stack runs on local minikube.
    - **Trino federated SQL** across Iceberg, BigQuery, and Faker catalogs, with OAuth2 SSO, fault-tolerant execution, and event listeners.

=== "Observability Engineering"

    - **Metrics.** `kube-prometheus` plus **Thanos** for long-term storage, backed by the same MinIO that serves the lakehouse.
    - **Traces.** OpenTelemetry Operator handles auto-instrumentation; Jaeger receives traces from both Trino and Thanos.
    - **GitOps-native.** Argo CD `app-of-apps` deploys the entire platform from a single commit.

## Architecture

![](architecture.drawio.svg)
/// caption
Architecture Overview
///

![](trino-otel.drawio.svg)
/// caption
Architecture Overview (Observability Engineering)
///

## Try it yourself

Reproduce the whole platform on your own Mac in two steps: install the tools listed in [Prerequisites](prerequisites.md), then run the one-shot bootstrap in [Deployment](deployment.md).
