---
tags:
  - Prometheus
  - Thanos
  - SRE
---
# How Thanos Works?


## Architecture Overview

- [Quick Tutorial](https://thanos.io/tip/thanos/quick-tutorial.md/) has a simple introduction to Thanos architecture and components.
- [Design](https://thanos.io/tip/thanos/design.md/) has a more detailed description of the architecture and components.

Thanos is comprised of a set of components where each fulfills a specific role

- **Sidecar**: connects to Prometheus, *remote reads its data for query* and/or *uploads it to cloud storage*.
- **Ruler**: **evaluates recording and alerting rules** against data in Thanos for exposition and/or upload. It can *discover query nodes* to evaluate recording and alerting rules.
- [**Store Gateway**](https://thanos.io/tip/thanos/design.md/#stores): Since *store nodes and data sources expose the same gRPC Store API*, clients can largely treat them as equivalent and don't have to be concerned with which specific component they are querying. It is purely a data retrieval API and does *not* provide complex query execution.
- [**Queriers**](https://thanos.io/tip/thanos/design.md/#query-layer): Queriers are **stateless and horizontally scalable instances** that implement **PromQL** on top of the Store APIs exposed in the cluster. Queriers participate in the cluster to be able to **resiliently discover all data sources and store nodes**. It implements **Prometheus's v1 API** to aggregate data. It is also capable of [***deduplicating*** data](https://thanos.io/tip/thanos/quick-tutorial.md/#deduplicating-data-from-prometheus-ha-pairs) collected from Prometheus HA pairs.
- [**Compactor**](https://thanos.io/tip/thanos/design.md/#compactor): a singleton process that does not participate in the Thanos cluster. Instead, it is only pointed at an object storage bucket and **continuously consolidates multiple smaller blocks into larger ones**. The compactor also does additional batch processing such as **down-sampling** and **applying retention policies**.
- **Receiver**: receives data from Prometheus's remote write WAL, exposes it, and/or uploads it to cloud storage.

```
┌────────────┬─────────┐         ┌────────────┬─────────┐     ┌─────────┐
│ Prometheus │ Sidecar │   ...   │ Prometheus │ Sidecar │     │   Rule  │
└────────────┴────┬────┘         └────────────┴────┬────┘     └┬────────┘
                  │                                │           │
                Blocks                           Blocks      Blocks
                  │                                │           │
                  v                                v           v
              ┌──────────────────────────────────────────────────┐
              │                   Object Storage                 │
              └──────────────────────────────────────────────────┘

```

```
┌──────────────────────┐  ┌────────────┬─────────┐   ┌────────────┐
│ Google Cloud Storage │  │ Prometheus │ Sidecar │   │    Rule    │
└─────────────────┬────┘  └────────────┴────┬────┘   └─┬──────────┘
                  │                         │          │
         Block File Ranges                  │          │
                  │                     Store API      │
                  v                         │          │
                ┌──────────────┐            │          │
                │     Store    │            │      Store API
                └────────┬─────┘            │          │
                         │                  │          │
                     Store API              │          │
                         │                  │          │
                         v                  v          v
                       ┌──────────────────────────────────┐
                       │              Client              │
                       └──────────────────────────────────┘
```

```
┌──────────────────┐  ┌────────────┬─────────┐   ┌────────────┐
│    Store Node    │  │ Prometheus │ Sidecar │   │    Rule    │
└─────────────┬────┘  └────────────┴────┬────┘   └─┬──────────┘
              │                         │          │
              │                         │          │
              │                         │          │
              v                         v          v
        ┌─────────────────────────────────────────────────────┐
        │                      Query layer                    │
        └─────────────────────────────────────────────────────┘
                ^                  ^                  ^
                │                  │                  │
       ┌────────┴────────┐  ┌──────┴─────┐       ┌────┴───┐
       │ Alert Component │  │ Dashboards │  ...  │ Web UI │
       └─────────────────┘  └────────────┘       └────────┘
```


!!! note

    - For a given Prometheus instance, it is *not* recommended to run both *Sidecar* and *Receiver* simultaneously.
    - If your goal is to have each Prometheus instance **self-manage** while still **allowing Querier to connect directly to each Prometheus for real-time data**, then the most natural choice is to use **Sidecar**. It sits alongside Prometheus, exposing data to Thanos Querier and handling the upload of historical blocks to object storage.
    - Conversely, if you want to **centralize the reception of metrics from multiple sources or tenants**, making the front-end Prometheus instances lighter, or planning a centralized write pipeline, then using **Receiver** is more appropriate. It uses `remote_write` to accept data from each Prometheus and maintains a unified storage and query interface on the backend.


## Behind the Scenes

### Thanos Receiver Deep Dive

<iframe width="560" height="315" src="https://www.youtube.com/embed/jn_zIfBuUyE?si=OTRBxGMJg_j87tOc" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
/// caption
Thanos Receiver Deep Dive - Joel Verezhak, Open Systems (2024)
///

<iframe width="560" height="315" src="https://www.youtube.com/embed/5MJqdJq41Ms?si=410RBLTt1Yb213M4" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
/// caption
Turn It Up to a Million: Ingesting Millions of Metrics with Thanos Receive - Lucas Servén Marín
///

<iframe width="560" height="315" src="https://www.youtube.com/embed/Sgv0fqy_AZk?si=isOAwtGiRBue1k5G" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
/// caption
Handling Billions of Metrics with Prometheus and Thanos - Ravi Hari & Amit Auddy, Intuit
///

### How Thanos Stores Data

- **Chunk Files**: hold a few hundred MB worth of chunks each. Chunks for the same series are sequentially aligned.
- **Index File**: holds all information needed to look up specific series
- `meta.json` File: holds meta-information about a block metadata

```
01BX6V6TY06G5MFQ0GPH7EMXRH
├── chunks
│   ├── 000001
│   ├── 000002
│   └── 000003
├── index
└── meta.json
```

See [Data in Object Storage](https://thanos.io/tip/thanos/storage.md/#data-in-object-storage) to understand how Thanos organizes data in object storage.


## References

- [Thanos | Prometheus Operator Docs](https://prometheus-operator.dev/docs/platform/thanos/)

