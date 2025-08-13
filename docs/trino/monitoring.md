---
tags:
  - Trino
---
# Monitoring with Prometheus and Grafana

## What is JMX?

**JMX (Java Management Extensions)** is a framework provided by Java for **monitoring and managing resources** while an application is running. When our application enables JMX, it starts a management interface inside the JVM, allowing you to **connect locally or remotely** to read the system and application runtime status, such as memory usage, thread count, and class loading statistics. It can also adjust application settings or execute specific operations without interrupting the service.

In JMX, an MBean is a managed object. For example, `MemoryMXBean` provides JVM memory-related information. These MBeans are registered in the **MBean Server** for external access. If remote management is required, JMX uses **RMI (Remote Method Invocation) to expose a remote access endpoint**. The **RMI Registry** records the names and locations of accessible MBean resources, and the **RMI Server** receives commands from remote clients and invokes the corresponding MBean methods.

In real-world projects, if we need to integrate JMX monitoring data into a monitoring system, a common approach is to deploy the **JMX Exporter**. It runs as a **Java Agent**, converting JMX data into a `/metrics` format readable by Prometheus, and exposes it over HTTP for Prometheus to scrape. Prometheus periodically collects these metrics, and Grafana uses the data from Prometheus to build visual dashboards, such as showing JVM heap usage, garbage collection counts, and other indicators.


<figure markdown="span">
  ![](https://upload.wikimedia.org/wikipedia/commons/2/29/JMX_Architecture.svg){width="500"}
</figure>

See [Getting Started with Java Management Extensions (JMX): Developing Management and Monitoring Solutions](https://www.oracle.com/technical-resources/articles/javase/jmx.html) for more details on JMX.

## What is JMX Exporter?

**JMX Exporter** is a specialized tool that bridges the gap between JMX monitoring data and modern observability platforms. Specifically, it serves as a process for collecting metrics using JMX MBeans and making them available for Prometheus consumption. At its core, the JMX Exporter acts as a collector that captures JMX MBean values and transforms them into a format that Prometheus can understand.

The JMX Exporter offers three distinct deployment approaches, each suited for different operational requirements:

- **Java Agent exporter**: First and most importantly, **the JMX Exporter Java agent runs directly as a Java agent within your application and collects JMX MBean values in real-time**. Notably, **the use of the JMX Exporter Java agent is strongly encouraged** due to the complex application RMI configuration that would otherwise be required when running the Standalone JMX Exporter.
- **Isolator Java Agent**: **Building upon the Java Agent approach**, the JMX Exporter Isolator Java agent provides enhanced flexibility by allowing you to **run multiple isolated and independent JMX Exporter Java agents simultaneously**. As a result, each isolated JMX Exporter Java agent can **maintain its own distinct configuration**, including separate ports, rules, and other settings.
- **Standalone exporter**: Alternatively, the Standalone JMX Exporter operates as a completely separate application that connects to your target application using RMI to collect JMX MBean values. However, this approach requires more complex RMI configuration compared to the Java Agent options.

Furthermore, both the Java Agent exporter and Isolator Java Agent support multiple operational modes to accommodate different monitoring architectures:

- **HTTP mode**: This mode collects metrics on-demand when accessed via HTTP requests, returning the metrics data as HTTP content. This represents a **pull** model where Prometheus actively scrapes the metrics endpoint.
- **OpenTelemetry mode**: In contrast, this mode periodically collects metrics and proactively pushes them to an OpenTelemetry endpoint. This follows a **push** model for metric delivery.
- **Combined mode**: Finally, this mode provides maximum flexibility by enabling both HTTP mode and OpenTelemetry mode metrics collection methods simultaneously.

See [`prometheus/jmx_exporter`](https://github.com/prometheus/jmx_exporter) for more details on JMX Exporter.


## References

- [Monitoring with JMX | Trino](https://trino.io/docs/current/admin/jmx.html)
- [Trino Monitoring (JMX) with Prometheus and Grafana](https://github.com/nil1729/trino-jmx-monitoring)