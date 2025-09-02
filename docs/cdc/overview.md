# Overview

![](../architecture.drawio.svg)
/// caption
Architecture Overview
///

This project is divided into several parts, one of which is the Change Data Capture (CDC) Pipeline. The main function of the CDC Pipeline is to capture database change data in real time and deliver it into Apache Iceberg tables, enabling downstream analytics and queries.

Specifically, we first deploy a Kafka Cluster to store real-time change data captured from the MySQL database. Next, we deploy a MySQL database to simulate the source of actual data write traffic. Then, we deploy the Debezium MySQL Source Connector on Kafka Connect to capture real-time change data from the MySQL database. Finally, we deploy the Iceberg Sink Connector on Kafka Connect to write the captured change data into Apache Iceberg tables.

!!! success "Deployment Steps"

    - [ ] [*Deploy a Kafka Cluster via the Strimzi Operator*](./cdc/deployment-kafka-cluster.md)
    - [ ] [*Deploy a MySQL Database*](./cdc/deployment-mysql.md)
    - [ ] [*Deploy a Debezium Kafka Source Connector*](./cdc/deployment-debezium-mysql-connector.md)
    - [ ] [*Deploy an Iceberg Kafka Sink Connector*](./cdc/deployment-iceberg-connector.md)
