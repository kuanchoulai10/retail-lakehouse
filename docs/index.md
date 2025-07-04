# Retail Lakehouse with Debezium, Kafka, Iceberg, and Trino

## 💡 Highlights

=== "Debezium Kafka Source Connector"

    !!! success "Highlights"

        - [x] Implemented **real-time, event-driven data pipelines** by capturing MySQL database change events (**CDC**) with **Debezium** and streaming them into **Kafka**, enabling downstream analytics.
        - [x] Designed a **non-intrusive CDC architecture** leveraging MySQL/PostgreSQL binary logs, requiring **no changes to source systems** while ensuring **exactly-once delivery** and **high fault tolerance** via **Kafka Connect**.
        - [x] Improved system **resilience** and **observability** through Debezium's **offset tracking and recovery features**, enabling **resumable** pipelines and reliable data integration across distributed environments.

=== "Kafka Cluster"

    !!! success "Highlights"

        - [x] Provisioned a **fault-tolerant** **Kafka cluster** on **Kubernetes** using the **Strimzi Operator**, enabling declarative configuration and seamless lifecycle management
        - [x] Enabled **KRaft** (Kafka Raft Metadata mode) with a **dual-role** cluster, removing dependency on ZooKeeper and simplifying cluster architecture
        - [x] Designed for **high availability** by replicating Kafka topics and internal state across multiple brokers using **replication factor** and **in-sync replicas (ISR)**.

=== "Iceberg Kafka Sink Connector"

    !!! success "Highlights"

        - [x] Ensured **centralized commit coordination** for Apache Iceberg via the Kafka Sink Connector, enabling consistent and atomic writes across distributed systems.
        - [x] Achieved **exactly-once delivery semantics** between Kafka and Iceberg tables, minimizing data duplication and ensuring data integrity.
        - [x] Utilized **`DebeziumTransform` SMT** to adapt Debezium CDC messages for compatibility with Iceberg's CDC feature, supporting real-time change propagation.
        - [x] Enabled **automatic table creation and schema evolution**, simplifying integration and reducing operational overhead when ingesting data into Iceberg tables.

=== "Iceberg Data Lakehouse"

    !!! success "Highlights"

        - [x] Adopted Apache Iceberg to bring ACID-compliant transactions and schema evolution to the data lake architecture.
        - [x] Managed Iceberg tables using **AWS Glue Data Catalog** as the catalog layer and **Amazon S3** as the storage layer.
        - [x] Enabled **data debugging** and **auditability** through Iceberg's time travel and snapshot rollback features.
        - [x] Implemented branching and tagging (WAP) to support isolated writes, data validation, and safe promotion in production workflows

=== "Trino"

    !!! success "Highlights"

        - [x] Integrated Trino to enable **federated SQL queries** across Apache Iceberg (S3) and external systems like BigQuery, **improving analytical agility**.
        - [x] Simplified **data access across multiple data sources without data duplication**, enabling ad-hoc analytics and reporting from a unified SQL interface.
        - [x] Integrated **Google OAuth 2.0** with Trino to enable **token-based authentication**, improving platform **auditability** and user **accountability**.

## Solution Architecture Overview

![](architecture.drawio.svg)

## Background

You are a solution architect at a fast-growing e-commerce company that processes hundreds of thousands of transactions and user interactions daily.

The current data setup is as follows:

- Order and transaction data is stored in **AWS RDS (MySQL)**.
- User behavioral data—such as product views, cart additions, and ad clicks—is collected via **Google Analytics 4 (GA4)** and streamed directly into **BigQuery**.
- The team is familiar with both **AWS** and **Google Cloud**, and **Amazon S3** is used as an intermediate storage layer for certain analytics workflows.

## Legacy Architecture

- Daily batch ETL jobs export data from RDS to feed internal reporting tools (e.g., Tableau or Google Looker Studio).
- GA4 user events are streamed into BigQuery in real time and queried for behavioral analytics.
- There is a clear **data silo** between MySQL and BigQuery, making it difficult to join and analyze user behavior alongside transactional data.
- Due to the large volume of data, the team prefers **not to move data unnecessarily** between systems to avoid latency and cost.

## Problems and Challenges

- Reporting **latency is too high** due to daily batch processing. Marketing teams cannot react in real time to campaign performance.
- There is **no unified way to analyze** both behavioral and transactional data together, which limits insight into user journeys and conversion paths.
- **Data duplication or migration across platforms is undesirable due to storage and operational costs**.
- There is **no centralized authentication or audit logging mechanism** to track query access and ensure data governance across multiple clouds.

## Business Requirements

- **Marketing teams** need real-time reports that combine website behavior and order data to quickly evaluate and adjust campaign performance.
- **Product managers** want to track funnel metrics like impressions, clicks, and conversions without waiting for daily batch reports.
- **Data analysts** need access to versioned, clean, and reliable data to support accurate ad-hoc analysis and troubleshoot issues when metrics look off.
- **IT and data governance teams** require secure, auditable access to data, with clear control over who can query what.