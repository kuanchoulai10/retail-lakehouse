---
tags:
  - Trino
---

# Fault-tolerant Execution in Trino

By default, when a Trino node experiences resource constraints or encounters failures while processing a query, the entire query fails and requires manual restart.

Fault-tolerant execution is a feature in Trino that helps clusters recover from query failures by automatically retrying failed queries or their individual tasks. When this capability is enabled, intermediate data exchanges are cached and stored, allowing other workers to reuse this data if a worker node fails or encounters issues during query execution.

<figure markdown="span">
  ![](./static/exchange-manager.drawio.svg){width="500"}
  **
</figure>


This allows Trino to handle larger queries such as **batch operations** without worker node interruptions causing the query to fail.

The **coordinator** node uses a configured **exchange manager** service that buffers data during query processing in an external location, such as an S3 object storage bucket. **Worker** nodes send data to the buffer as they execute their query tasks.


##
- only read support: other connectors
- read and write support 
    - MySQL connector
    - PostgreSQL connector
    - SQL Server connector
    - Hive connector
    - Delta Lake connector
    - Iceberg connector
- It is recommended to run a dedicated fault-tolerant cluster for handling batch operations, separate from a cluster that is designated for a higher query volume. As a best practice, it is recommended to run a dedicated cluster with a TASK retry policy for large batch queries, separate from another cluster that handles short queries.
- The exchange manager may send a large amount of data to the exchange storage, resulting in high I/O load on that storage. You can configure multiple storage locations for use by the exchange manager to help balance the I/O load between them.
- When fault-tolerant execution is enabled on a cluster, write operations fail on any catalogs that do not support fault-tolerant execution of those operations.


## References

- [Improve query processing resilience](https://trino.io/docs/current/installation/query-resiliency.html)
- [Fault-tolerant execution](https://trino.io/docs/current/admin/fault-tolerant-execution.html)
- [Exchange properties](https://trino.io/docs/current/admin/properties-exchange.html)