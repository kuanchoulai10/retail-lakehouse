# Retail Lakehouse with Debezium, Kafka, Iceberg, and Trino

A streaming data pipeline that simulates a global e-commerce inventory system. This project uses **Debezium** and **Kafka** to capture real-time changes (CDC) from a PostgreSQL database and writes them into a unified **Iceberg** lakehouse table. **Trino** enables fast, federated SQL analytics on the evolving dataset.

## Architecture Overview

![](architecture.drawio.svg)

## Use Case: Global Retail Inventory Sync

Imagine an international e-commerce company with separate inventory databases per region (e.g., US, EU, ASIA). This system continuously syncs inventory changes into a central Iceberg table for analytics and reporting — without batch jobs.


## Features

- Real-time inventory synchronization via **Debezium**
- Query data instantly with **Trino** using ANSI SQL
- Pluggable catalog support (e.g., REST, Hive)
- Cloud-native deployment using Kubernetes
