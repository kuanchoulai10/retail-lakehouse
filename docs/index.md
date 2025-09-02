---
tags:
  - Debizium
  - Apache Kafka
  - Apache Iceberg
  - Apache Spark
  - Trino
---
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

## 🏗️ Architecture

![](architecture.drawio.svg)
/// caption
Architecture Overview
///

## 🗂️ What's Inside?

First, clone the repository:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone git@github.com:kuanchoulai10/retail-lakehouse.git
```

The project structure looks like this:

```
.
├── kafka-cluster
├── mysql
├── kafka-debezium-mysql-connector
├── kafka-iceberg-connector
├── trino
├── spark
└── prometheus-grafana
```

## 📑 Deployment Steps

The basic deployment path includes the following steps:

!!! success "Deployment Steps"

    - [ ] Deploy a Kafka Cluster via the Strimzi Operator
    - [ ] Deploy a MySQL Database
    - [ ] Deploy a Debezium Kafka Source Connector
    - [ ] Deploy an Iceberg Kafka Sink Connector
    - [ ] Deploy a Trino Cluster
    - [ ] Deploy a Spark Cluster (WIP)
    - [ ] Deploy Prometheus and Grafana (WIP)
