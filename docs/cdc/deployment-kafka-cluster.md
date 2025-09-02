# Kafka Cluster Deployment

![](../architecture.drawio.svg)
/// caption
Architecture Overview
///

!!! success "Deployment Steps"

    - [ ] [*Deploy a Kafka Cluster via the Strimzi Operator*](./cdc/deployment-kafka-cluster.md)
    - [ ] [*Deploy a MySQL Database*](./cdc/deployment-mysql.md)
    - [ ] [*Deploy a Debezium Kafka Source Connector*](./cdc/deployment-debezium-mysql-connector.md)
    - [ ] [*Deploy an Iceberg Kafka Sink Connector*](./cdc/deployment-iceberg-connector.md)


Without further ado, let's jump straight to the commands:

```bash
cd ~/Projects/retail-lakehouse/kafka-cluster
bash install.sh
```

??? info "install.sh"

    ```bash
    --8<-- "./kafka-cluster/install.sh"
    ```

This script will deploy a Kafka Cluster using the Strimzi Operator in the `kafka-cdc` namespace.

If you don't like my script and want to do it step by step manually, please continue reading. This article will walk you through how to deploy a Kafka Cluster using the Strimzi Operator on Kubernetes step by step, explaining each part along the way.



## Deploy the Strimzi Cluster Operator

Before we dive into deploying Kafka, let's talk about *what Strimzi is* and *why we need it*. 

**Strimzi is a Kubernetes operator that makes running Apache Kafka on Kubernetes much easier**. Think of it as your Kafka cluster manager and it handles all the complex setup, configuration, and maintenance tasks that would otherwise require manual intervention.

Instead of manually creating Kafka pods, services, and configurations, Strimzi lets you define what you want in simple YAML files, and it takes care of the rest.

You can deploy Strimzi on Kubernetes 1.25 and later using one of the following methods:

- [ ] Deployment files (YAML files)
- [ ] OperatorHub.io
- [x] Helm chart

In this guide, we'll use the Helm chart method because it's straightforward and allows for easy customization.

First, we need to create two separate Kubernetes namespaces, one for the Strimzi operator and another for our Kafka cluster:

```bash
kubectl create namespace strimzi
kubectl create namespace kafka-cdc
```

Next, we need to add the Strimzi Helm repository to our local Helm setup and install the Strimzi operator with our custom values:

```bash
helm repo add strimzi https://strimzi.io/charts/
helm install \
  strimzi-cluster-operator \
  oci://quay.io/strimzi-helm/strimzi-kafka-operator \
  -f ~/Projects/retail-lakehouse/kafka-cluster/values.yaml \
  -n strimzi \
  --version 0.46.1
```

Here's our customized `values.yaml` file and the most important settings is `watchNamespaces`, which tells Strimzi to specifically watch the `kafka-cdc` namespace where we'll deploy our Kafka cluster.

??? info "values.yaml"

    ```yaml linenums="1" hl_lines="8 9"
    --8<-- "./kafka-cluster/values.yaml"
    ```

If everything goes well, you'll see output like this:

??? info "Result"

    ```
    Pulled: quay.io/strimzi-helm/strimzi-kafka-operator:0.46.1
    Digest: sha256:e87ea2a03985f5dd50fee1f8706f737fa1151b86dce5021b6c0798ac8b17e27f
    NAME: {==strimzi-cluster-operator==}
    LAST DEPLOYED: Sun Jun 29 17:25:49 2025
    NAMESPACE: strimzi
    STATUS: deployed
    REVISION: 1
    TEST SUITE: None
    NOTES:
    Thank you for installing {==strimzi-kafka-operator-0.46.1==}

    To create a Kafka cluster refer to the following documentation.

    https://strimzi.io/docs/operators/latest/deploying.html#deploying-cluster-operator-helm-chart-str
    ```

Great! The `STATUS: deployed` tells us everything went smoothly.

Let's make sure our Strimzi operator is actually running:

```bash
helm ls -n strimzi
```

??? info "Result"

    ```
    NAME                    	NAMESPACE	REVISION	UPDATED                             	STATUS  	HART                        	APP VERSION
    strimzi-cluster-operator	strimzi  	1       	2025-06-29 17:25:49.773026 +0800 CST	deployed	trimzi-kafka-operator-0.46.1	0.46.1     
    ```

```bash
kubectl get all -n strimzi
```

??? info "Result"

    ```
    NAME                                           READY   STATUS    RESTARTS   AGE
    pod/strimzi-cluster-operator-74f577b78-s9n25   1/1     Running   0          108s

    NAME                                           READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/strimzi-cluster-operator       1/1     1            1           108s

    NAME                                                 DESIRED   CURRENT   READY   AGE
    replicaset.apps/strimzi-cluster-operator-74f577b78   1         1         1       108s
    ```

Perfect! At this point, the Strimzi operator is running and watching for Kafka-related resources in the `kafka-cdc` namespace. It's like having a dedicated Kafka administrator ready to spring into action whenever we create Kafka clusters or related components.



## Deploy a Kafka Cluster

Now that we have Strimzi operator running, let's deploy our actual Kafka cluster!

```bash
kubectl create -f kafka-cluster.yaml -n kafka-cdc
```

This command tells Kubernetes to create both the Kafka cluster and the node pool in our `kafka-cdc` namespace. You should see output confirming both resources were created:

??? info "Result"

    ```
    kafka.kafka.strimzi.io/kafka-cluster created
    kafkanodepool.kafka.strimzi.io/dual-role created
    ```

Kafka clusters take a bit of time to start up - they need to elect controllers, establish consensus, and create internal topics. Let's check on the progress:

```bash
kubectl get all -n kafka-cdc
```

Initially, you might see pods in `Pending` or `ContainerCreating` status. After a minute or two, you should see something like this:

??? info "Result"

    ```
    NAME                                                    READY   STATUS    RESTARTS   AGE
    pod/kafka-cluster-dual-role-0                           1/1     Running   0          60s
    pod/kafka-cluster-dual-role-1                           1/1     Running   0          60s
    pod/kafka-cluster-dual-role-2                           1/1     Running   0          60s
    pod/kafka-cluster-entity-operator-5b998f6cbf-c8hdf      2/2     Running   0          24s

    NAME                                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                        AGE
    service/kafka-cluster-kafka-bootstrap      ClusterIP   10.105.50.103   <none>        9091/TCP,9092/TCP,9093/TCP                     61s
    service/kafka-cluster-kafka-brokers        ClusterIP   None            <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   61s

    NAME                                               READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/kafka-cluster-entity-operator      1/1     1            1           24s

    NAME                                                          DESIRED   CURRENT   READY   AGE
    replicaset.apps/kafka-cluster-entity-operator-5b998f6cbf      1         1         1       24s
    ```

    **Components of the Kafka Cluster**:

    - *Three Kafka Pods*: These are your dual-role nodes, numbered 0, 1, and 2
    - *Entity Operator*: This Strimzi component manages Kafka topics and users for you
    - *Bootstrap Service*: This is how clients discover and connect to your Kafka cluster
    - *Broker Service*: This provides direct access to individual brokers when needed

If you are interested in how the Kafka cluster is configured, you can continue reading the next section. If not, you are good to go to the next step: [*Deploy a MySQL Database*](./deployment-mysql.md).



### Deep Dive: Understanding the Kafka Configuration

Let's break down what this configuration is telling Kubernetes to create for us.



#### Version

??? info "kafka-cluster.yaml:cluster"

    ```yaml
    --8<-- "./kafka-cluster/kafka-cluster.yaml:cluster"
    ```

We're using **Kafka 4.0**. The `spec.kafka.metadataVersion: 4.0-IV3` setting is important (the "IV" stands for "Incompatible Version," which means this version has significant metadata structure changes that aren't backward compatible). We need to explicitly specify this to confirm we understand we're using the latest format.



#### Fault Tolerance and Consistency

??? info "kafka-cluster.yaml:cluster"

    ```yaml
    --8<-- "./kafka-cluster/kafka-cluster.yaml:cluster"
    ```

The configuration section ensures our cluster is production-ready with proper replication and consistency guarantees via settings under `spec.kafka.config`:

- `default.replication.factor: 3`
- `offsets.topic.replication.factor: 3`
- `transaction.state.log.replication.factor: 3`

We're telling Kafka to keep `3` copies of everything, including your regular topics, consumer offset tracking, and transaction state. This means we can lose one broker and still have all our data.

- `transaction.state.log.min.isr: 2`
- `min.insync.replicas: 2`

These configurations ensure that at least `2` replicas must acknowledge a write before it's considered successful. This prevents data loss even if a broker fails right after acknowledging a write.



#### Listeners: How Clients Connect

??? info "kafka-cluster.yaml:cluster"

    ```yaml
    --8<-- "./kafka-cluster/kafka-cluster.yaml:cluster"
    ```

Our configuration sets up two ways for applications to connect to Kafka:

**Plain Listener (port `9092`)**

: This is your standard, unencrypted connection. Perfect for development environments, internal applications where network security is handled at other layers, and high-throughput scenarios where TLS overhead isn't desired.

**TLS Listener (port `9093`)**

: This provides encrypted connections for, cross-namespace communication, production environments with security requirements, any scenario where data in transit needs protection.



#### KRaft Mode

??? info "kafka-cluster.yaml"

    ```yaml
    --8<-- "./kafka-cluster/kafka-cluster.yaml"
    ```

If you're coming from a traditional Kafka background, you might be expecting to see ZooKeeper configurations, but we're going to use Kafka's newer **KRaft mode** instead. Think of KRaft as Kafka's way of saying "*I don't need ZooKeeper anymore. I can manage my own metadata.*"

??? abstract "Understanding KRaft Mode"

    If you've worked with Kafka before, you might remember the pain of managing ZooKeeper alongside your Kafka clusters. **KRaft mode eliminates that complexity entirely**. Here's what makes it special:

    **What KRaft Replaces**:
    
    Instead of relying on an external ZooKeeper ensemble to store Kafka's metadata (like topic configurations, partition assignments, and cluster membership), **Kafka brokers now handle this responsibility themselves using a consensus algorithm similar to Raft**.

    **Why This Matters**:

    - **Simplified Operations**: One less system to deploy, monitor, and troubleshoot
    - **Better Performance**: No more network hops to ZooKeeper for metadata operations
    - **Improved Reliability**: Fewer moving parts means fewer potential failure points

To enable KRaft mode in Strimzi, we add two key annotations to our `Kafka` resource:

- `strimzi.io/node-pools: enabled`: Tells Strimzi we want to use the newer node pool architecture
- `strimzi.io/kraft: enabled`: Enables KRaft mode instead of ZooKeeper

The configuration file we'll use defines not just a `Kafka` cluster, but also something called a `KafkaNodePool`. *This is Strimzi's way of letting you organize your Kafka nodes into different groups with different roles and storage configurations*. It lets you organize your Kafka nodes into logical groups.

In our case, we're creating a `dual-role` node pool with 3 nodes where **each node acts as both a Controller (managing metadata) and a Broker (handling client data traffic)**.

Why choose dual-role nodes?

- **Resource Efficient**: Fewer total machines needed
- **Simpler Architecture**: No need to separate controller and broker concerns
- **Still Highly Available**: With 3 nodes, we can tolerate losing one node

Each node gets a `100GB` persistent volume that stores both regular Kafka logs and KRaft metadata. The `spec.storage.volumes.kraftMetadata: shared` setting means **both types of data live on the same disk, which is fine for most use cases**.

---

## Conclusion

Congratulations! You now have a fully functional Kafka cluster running in KRaft mode.

In the next section, we'll deploy a MySQL database that will serve as our data source for change data capture.



## References

- [Deploying Debezium on Kubernetes | Debezium Documentation](https://debezium.io/documentation//reference/stable/operations/kubernetes.html)
- [Deploying and Managing | Strimzi Documentation](https://strimzi.io/docs/operators/latest/deploying)
- [Using the Iceberg framework in AWS Glue | AWS](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-format-iceberg.html)
- [Iceberg Kafka Connector | Iceberg](https://iceberg.apache.org/docs/latest/kafka-connect/)