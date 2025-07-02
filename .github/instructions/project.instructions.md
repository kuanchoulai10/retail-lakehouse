---
applyTo: '**'
---
# Project Overview

This project implements a retail lakehouse architecture that captures real-time MySQL database changes using Debezium CDC through a 3-node Kafka cluster (KRaft mode) managed by Strimzi Operator on Kubernetes.

Data flows from MySQL -> Debezium Kafka Source Connector -> Kafka Cluster -> Iceberg Kafka Sink Connector -> Apache Iceberg tables, with AWS S3 as storage layer and AWS Glue Data Catalog for catalog layer.

Each Kafka connector runs in its own dedicated Kafka Connect cluster—one Kafka Connect cluster hosts the Debezium Source Connector, and another distinct Kafka Connect cluster hosts the Iceberg Sink Connector.

## Transactional Database
- Database engine: MySQL
- Purpose: Serves as the source of transactional data for CDC

## Strimzi Operator
- Deployment method: Installed via Helm in the `strimzi` namespace
- Strimzi version: 0.46.1
- Purpose: Manages and operates the Kafka cluster and related components

##  Kafka Cluster
- Kafka namespace: `kafka-cdc`
- Kafka version: 4.0.0
- Kafka cluster setup: 3 brokers, running in KRaft (dual-role) mode
- Purpose: Acts as the central message broker for capturing and distributing change events

## Debezium Kafka Source Connector
- Connector type: Debezium Kafka Source Connector
- Kafka Connect version: 4.0.0
- Deployment: Runs in a dedicated Kafka Connect cluster
- Purpose: Captures change events from the MySQL database and publishes them to Kafka topics

## Iceberg Kafka Sink Connector
- Iceberg version: 1.9.1
- Connector type: Apache Iceberg Kafka Sink Connector
- Kafka Connect version: 4.0.0
- Deployment: Runs in a separate dedicated Kafka Connect cluster
- Purpose: Consumes change events from Kafka topics and writes them to Apache Iceberg tables

## Iceberg Table
- Iceberg version: 1.9.1
- Catalog layer: AWS Glue Data Catalog
- Storage layer: AWS S3
- Purpose: Stores curated and queryable data in a lakehouse format
