# MySQL Deployment

![](../architecture.drawio.svg)
/// caption
Architecture Overview
///

Make sure you have deployed a Kafka cluster first.

!!! success "Deployment Steps"

    - [x] [*Deploy a Kafka Cluster via the Strimzi Operator*](./cdc/deployment-kafka-cluster.md)
    - [ ] [*Deploy a MySQL Database*](./cdc/deployment-mysql.md)
    - [ ] [*Deploy a Debezium Kafka Source Connector*](./cdc/deployment-debezium-mysql-connector.md)
    - [ ] [*Deploy an Iceberg Kafka Sink Connector*](./cdc/deployment-iceberg-connector.md)

After the Kafka cluster is up and running, you can deploy MySQL by running the following commands:

```bash
bash ~/Projects/retail-lakehouse/mysql/install.sh
```

??? info "Result"

    ```
    service/mysql created
    deployment.apps/mysql created
    ```

The `install.sh` script in the `mysql` directory is as follows:

??? info "install.sh"

    ```bash
    --8<-- "./mysql/install.sh"
    ```

You can check the `mysql.yaml` file in the `mysql` directory:

??? info "mysql.yaml"

    ```yaml
    --8<-- "./mysql/mysql.yaml"
    ```

To verify that MySQL is running, you can use the following command:

```bash
kubectl get all -n kafka-cdc
```

??? info "Result"

    ```
    NAME                                                    READY   STATUS    RESTARTS   AGE
    pod/kafka-cluster-dual-role-0                           1/1     Running   0          15m
    pod/kafka-cluster-dual-role-1                           1/1     Running   0          15m
    pod/kafka-cluster-dual-role-2                           1/1     Running   0          15m
    pod/kafka-cluster-entity-operator-5b998f6cbf-c8hdf      2/2     Running   0          15m
    {==pod/mysql-6b84fd947d-9g9lt==}                              1/1     Running   0          10m

    NAME                                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                        AGE
    service/kafka-cluster-kafka-bootstrap      ClusterIP   10.105.50.103   <none>        9091/TCP,9092/TCP,9093/TCP                     15m
    service/kafka-cluster-kafka-brokers        ClusterIP   None            <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   15m
    {==service/mysql==}                              ClusterIP   None            <none>        3306/TCP                                       10m

    NAME                                               READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/kafka-cluster-entity-operator      1/1     1            1           15m
    {==deployment.apps/mysql==}                              1/1     1            1           10m

    NAME                                                          DESIRED   CURRENT   READY   AGE
    replicaset.apps/kafka-cluster-entity-operator-5b998f6cbf      1         1         1       15m
    {==replicaset.apps/mysql-6b84fd947d==}                              1         1         1       10m
    ```