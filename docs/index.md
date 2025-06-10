# Retail Lakehouse with Flink, Kafka, Iceberg, and Trino

A streaming-first data pipeline that simulates a global e-commerce inventory system. This project uses **Flink** and **Kafka** to capture real-time changes (CDC) from multiple regional PostgreSQL databases and writes them into a unified **Iceberg** lakehouse table. **Trino** enables fast, federated SQL analytics on the evolving dataset.

## Architecture Overview

```
PostgreSQL (CDC)
        ↓
Flink + Kafka
        ↓
Apache Iceberg (Lakehouse Table)
        ↓
     Trino
```

## Use Case: Global Retail Inventory Sync

Imagine an international e-commerce company with separate inventory databases per region (e.g., US, EU, ASIA). This system continuously syncs inventory changes into a central Iceberg table for analytics and reporting — without batch jobs.

## Tech Stack

| Layer             | Technology                   |
|-------------------|------------------------------|
| Change Capture    | Flink CDC, Kafka Connect     |
| Stream Processing | Apache Flink                 |
| Storage Format    | Apache Iceberg (local/HDFS/S3) |
| Query Engine      | Trino                        |
| Databases         | PostgreSQL (simulated CDC)  |

## Features

- Real-time inventory synchronization via **Flink CDC**
- Append-only Iceberg table with full snapshot tracking
- Query data instantly with **Trino** using ANSI SQL
- Pluggable catalog support (e.g., REST, Hive)
- Cloud-native deployment using Kubernetes
