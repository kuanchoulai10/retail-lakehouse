---
tags:
  - Trino
---

# Join Optimization

## Join Enumeration

Understanding `JOIN` optimization is crucial because **`JOIN` order significantly impacts performance, particularly affecting intermediate result sizes and network transfer volumes**. Different join orders can lead to vastly different intermediate result sizes. When you start with a `JOIN` that produces a massive intermediate table, each subsequent step requires moving and processing more data, resulting in slower performance and higher resource consumption. Conversely, starting with a `JOIN` that produces a small intermediate table leads to much better performance.

To address this challenge, **Trino includes Cost-Based Join Enumeration by default**. This algorithm uses **table statistics** (row counts, sizes, distributions) to estimate the cost of each possible `JOIN` order. **It enumerates all possible `JOIN` execution sequences, compares their costs, and selects the most resource-efficient order.** The system automatically chooses the lowest-cost (fastest) `JOIN` sequence for execution. **This means the `JOIN` order you write in your SQL statements won't affect Trino's execution plan, Trino will automatically select the optimal `JOIN` order**.

However, accurate table statistics are essential for Trino to correctly estimate costs. **You can initialize these statistics using the [`ANALYZE`](https://trino.io/docs/current/sql/analyze.html) command.** This enables Trino to make optimal `JOIN` order decisions based on the latest data distribution and sizes.


## Join Distribution

Beyond join order optimization, **Trino must also determine how to distribute data across nodes during `JOIN` execution**. Since Trino is a distributed query engine with multiple nodes processing queries collaboratively, **`JOIN` operations require data from both tables to be located on the same node for comparison and hash table construction.**

Trino uses a **hash-based join algorithm** where the system first designates one side as **the build side**, loading all its data into memory and creating a hash table based on the join key. The other side becomes **the probe side**, with the system reading its data row by row and querying the hash table using the join key to find matching rows and output results. This method is particularly effective when sufficient memory is available, and **typically uses the smaller dataset as the build side to reduce memory usage and improve performance**.

There are two main types of join distributions:

- **Partitioned joins**: Each node participating in the query builds a hash table from **only a fraction of the data**. This approach requires **redistributing both tables** using a hash of the join key. While these joins can be **slower** than broadcast joins, they enable **much larger joins overall**.
- **Broadcast joins**: Each node participating in the query builds a hash table from all the data, with data replicated to each node. **Broadcast joins perform better when the build side is much smaller than the probe side**. However, **they require that build-side tables fit in memory** on each node after filtering, whereas partitioned joins only need to fit in distributed memory across all nodes.

!!! info

    Trino's cost-based optimization automatically handles these decisions. With **cost-based join distribution selection**, Trino automatically chooses between **partitioned and broadcast joins**. Similarly, **cost-based join enumeration** automatically determines which sides serve as **probe and build**.


!!! info "Configuration"

    Join enumeration strategy is controlled by `join_reordering_strategy` session property (or `optimizer.join-reordering-strategy` config)
    
    - `AUTOMATIC` (default)
    - `ELIMINATE_CROSS_JOINS`
    - `NONE`.
    
    Join distribution strategy uses `join_distribution_type` session property (or `join-distribution-type` config)
    
    - `AUTOMATIC` (default)
    - `BROADCAST`
    - `PARTITIONED`.
    
    Replicated table size can be capped using `join_max_broadcast_table_size` session property (or `join-max-broadcast-table-size` config): defaulting to 100MB.

    See [Cost-based optimizations](https://trino.io/docs/current/optimizer/cost-based-optimizations.html) for more details.