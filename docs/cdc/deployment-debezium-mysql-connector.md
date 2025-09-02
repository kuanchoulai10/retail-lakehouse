# Debezium MySQL Kafka Connector Deployment

![](../architecture.drawio.svg)
/// caption
Architecture Overview
///

Make sure you have deployed a Kafka cluster and a MySQL database first.

!!! success "Deployment Steps"

    - [x] [*Deploy a Kafka Cluster via the Strimzi Operator*](./cdc/deployment-kafka-cluster.md)
    - [x] [*Deploy a MySQL Database*](./cdc/deployment-mysql.md)
    - [ ] [*Deploy a Debezium Kafka Source Connector*](./cdc/deployment-debezium-mysql-connector.md)
    - [ ] [*Deploy an Iceberg Kafka Sink Connector*](./cdc/deployment-iceberg-connector.md)

After the Kafka cluster and MySQL database are up and running, you can deploy the Debezium MySQL Kafka Connector


## Create Secrets for the Database

```yaml title="debezium-secret.yaml" linenums="1" hl_lines="4"
--8<-- "./kafka-cluster/debezium-secret.yaml"
```

```yaml title="debezium-role.yaml" linenums="1" hl_lines="4 9"
--8<-- "./kafka-cluster/debezium-role.yaml"
```

```yaml title="debezium-role-binding.yaml" linenums="1" hl_lines="4 8 12"
--8<-- "./kafka-cluster/debezium-role-binding.yaml"
```

```bash
kubectl apply -f debezium-secret.yaml
kubectl apply -f debezium-role.yaml
kubectl apply -f debezium-role-binding.yaml
```

```
secret/debezium-secret created
role.rbac.authorization.k8s.io/debezium-role created
rolebinding.rbac.authorization.k8s.io/debezium-role-binding created
```

## Create a Debezium Kafka Connect Cluster

To deploy a Debezium connector, you need to deploy a Kafka Connect cluster with the required connector plug-in(s), before instantiating the actual connector itself.

As the first step, a container image for Kafka Connect with the plug-in has to be created.

Strimzi also can be used for building and pushing the required container image for us. In fact, both tasks can be merged together and instructions for building the container image can be provided directly within the `KafkaConnect` object specification:

```bash
minikube addons enable registry
```

```
💡  registry is an addon maintained by minikube. For any concerns contact minikube on GitHub.
You can view the list of minikube maintainers at: https://github.com/kubernetes/minikube/blob/master/OWNERS
╭──────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                      │
│    Registry addon with docker driver uses port 49609 please use that instead of default port 5000    │
│                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────╯
📘  For more information see: https://minikube.sigs.k8s.io/docs/drivers/docker
    ▪ Using image docker.io/registry:2.8.3
    ▪ Using image gcr.io/k8s-minikube/kube-registry-proxy:0.0.6
🔎  Verifying registry addon...
🌟  The 'registry' addon is enabled
```

```bash
kubectl -n kube-system get svc registry -o jsonpath='{.spec.clusterIP}'

10.104.128.211
```

```yaml title="debezium-connect-cluster.yaml"
--8<-- "./kafka-cluster/debezium-connect-cluster.yaml"
```

```bash
kubectl apply -f debezium-connect-cluster.yaml -n kafka-cdc
```

```
kafkaconnect.kafka.strimzi.io/debezium-connect-cluster created
```

Check the current resources in the `kafka-cdc` namespace:

```bash
kubectl get all -n kafka-cdc
```

```
NAME                                                    READY   STATUS    RESTARTS   AGE
pod/kafka-cluster-dual-role-0                           1/1     Running   0          66m
pod/kafka-cluster-dual-role-1                           1/1     Running   0          66m
pod/kafka-cluster-dual-role-2                           1/1     Running   0          66m
pod/kafka-cluster-entity-operator-5b998f6cbf-c8hdf      2/2     Running   0          65m
{==pod/debezium-connect-cluster-connect-build==}              1/1     Running   0          49s
pod/mysql-6b84fd947d-9g9lt                              1/1     Running   0          60m

NAME                                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                        AGE
service/kafka-cluster-kafka-bootstrap      ClusterIP   10.105.50.103   <none>        9091/TCP,9092/TCP,9093/TCP                     66m
service/kafka-cluster-kafka-brokers        ClusterIP   None            <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   66m
service/mysql                              ClusterIP   None            <none>        3306/TCP                                       60m

NAME                                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/kafka-cluster-entity-operator      1/1     1            1           65m
deployment.apps/mysql                              1/1     1            1           60m

NAME                                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/kafka-cluster-entity-operator-5b998f6cbf      1         1         1       65m
replicaset.apps/mysql-6b84fd947d                              1         1         1       60m
```

過一陣子後

```
NAME                                                    READY   STATUS    RESTARTS   AGE
pod/kafka-cluster-dual-role-0                           1/1     Running   0          100m
pod/kafka-cluster-dual-role-1                           1/1     Running   0          100m
pod/kafka-cluster-dual-role-2                           1/1     Running   0          100m
pod/kafka-cluster-entity-operator-5b998f6cbf-c8hdf      2/2     Running   0          99m
{==pod/debezium-connect-cluster-connect-0==}                  1/1     Running   0          30m
pod/mysql-6b84fd947d-9g9lt                              1/1     Running   0          94m

NAME                                           TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                                        AGE
service/kafka-cluster-kafka-bootstrap          ClusterIP   10.105.50.103    <none>        9091/TCP,9092/TCP,9093/TCP                     100m
service/kafka-cluster-kafka-brokers            ClusterIP   None             <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   100m
{==service/debezium-connect-cluster-connect==}       ClusterIP   None             <none>        8083/TCP                                       30m
{==service/debezium-connect-cluster-connect-api==}   ClusterIP   10.100.229.177   <none>        8083/TCP                                       30m
service/mysql                                  ClusterIP   None             <none>        3306/TCP                                       94m

NAME                                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/kafka-cluster-entity-operator      1/1     1            1           99m
deployment.apps/mysql                              1/1     1            1           94m

NAME                                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/kafka-cluster-entity-operator-5b998f6cbf      1         1         1       99m
replicaset.apps/mysql-6b84fd947d                              1         1         1       94m
```


## Create a Debezium Source Connector

```yaml title="debezium-connector.yaml"
--8<-- "./kafka-cluster/debezium-connector.yaml"
```

```bash
kubectl apply -f debezium-connector.yaml -n kafka-cdc
```

```
kafkaconnector.kafka.strimzi.io/debezium-connector created
```

```bash
kubectl get kafkaconnector debezium-connector -n kafka-cdc

NAME                 CLUSTER                    CONNECTOR CLASS                              MAX TASKS   READY
debezium-connector   debezium-connect-cluster   io.debezium.connector.mysql.MySqlConnector   1           True
```

## Verify the CDC Pipeline

```bash
kubectl run kafka-topics-cli \
  -n kafka-cdc \
  -it --rm \
  --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 \
  --restart=Never -- \
  bin/kafka-topics.sh \
    --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
    --list
```

??? info "Result"

    ```
    __consumer_offsets
    debezium-cluster-configs
    debezium-cluster-offsets
    debezium-cluster-status
    mysql
    mysql.inventory.addresses
    mysql.inventory.customers
    mysql.inventory.geom
    mysql.inventory.orders
    mysql.inventory.products
    mysql.inventory.products_on_hand
    schema-changes.inventory
    ```


```bash
kubectl run kafka-cli \
  -n kafka-cdc \
  -it --rm \
  --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 \
  --restart=Never -- \
  bin/kafka-console-consumer.sh \
    --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
    --topic mysql.inventory.customers \
    --partition 0
    --offset -10
    --max-messages 10
```

```bash
kubectl exec -n kafka-cdc -it mysql-6b84fd947d-9g9lt -- mysql -uroot -pdebezium
```

```bash
sql> use inventory;
sql> update customers set first_name="Sally Marie" where id=1001;
```

??? info "Result"

    ```json
    {
    "schema": {
        "type": "struct",
        "fields": [
        {
            "type": "struct",
            "fields": [
            {
                "type": "int32",
                "optional": false,
                "field": "id"
            },
            {
                "type": "string",
                "optional": false,
                "field": "first_name"
            },
            {
                "type": "string",
                "optional": false,
                "field": "last_name"
            },
            {
                "type": "string",
                "optional": false,
                "field": "email"
            }
            ],
            "optional": true,
            "name": "mysql.inventory.customers.Value",
            "field": "before"
        },
        {
            "type": "struct",
            "fields": [
            {
                "type": "int32",
                "optional": false,
                "field": "id"
            },
            {
                "type": "string",
                "optional": false,
                "field": "first_name"
            },
            {
                "type": "string",
                "optional": false,
                "field": "last_name"
            },
            {
                "type": "string",
                "optional": false,
                "field": "email"
            }
            ],
            "optional": true,
            "name": "mysql.inventory.customers.Value",
            "field": "after"
        },
        {
            "type": "struct",
            "fields": [
            {
                "type": "string",
                "optional": false,
                "field": "version"
            },
            {
                "type": "string",
                "optional": false,
                "field": "connector"
            },
            {
                "type": "string",
                "optional": false,
                "field": "name"
            },
            {
                "type": "int64",
                "optional": false,
                "field": "ts_ms"
            },
            {
                "type": "string",
                "optional": true,
                "name": "io.debezium.data.Enum",
                "version": 1,
                "parameters": {
                "allowed": "true,first,first_in_data_collection,last_in_data_collection,last,false,incremental"
                },
                "default": "false",
                "field": "snapshot"
            },
            {
                "type": "string",
                "optional": false,
                "field": "db"
            },
            {
                "type": "string",
                "optional": true,
                "field": "sequence"
            },
            {
                "type": "int64",
                "optional": true,
                "field": "ts_us"
            },
            {
                "type": "int64",
                "optional": true,
                "field": "ts_ns"
            },
            {
                "type": "string",
                "optional": true,
                "field": "table"
            },
            {
                "type": "int64",
                "optional": false,
                "field": "server_id"
            },
            {
                "type": "string",
                "optional": true,
                "field": "gtid"
            },
            {
                "type": "string",
                "optional": false,
                "field": "file"
            },
            {
                "type": "int64",
                "optional": false,
                "field": "pos"
            },
            {
                "type": "int32",
                "optional": false,
                "field": "row"
            },
            {
                "type": "int64",
                "optional": true,
                "field": "thread"
            },
            {
                "type": "string",
                "optional": true,
                "field": "query"
            }
            ],
            "optional": false,
            "name": "io.debezium.connector.mysql.Source",
            "version": 1,
            "field": "source"
        },
        {
            "type": "struct",
            "fields": [
            {
                "type": "string",
                "optional": false,
                "field": "id"
            },
            {
                "type": "int64",
                "optional": false,
                "field": "total_order"
            },
            {
                "type": "int64",
                "optional": false,
                "field": "data_collection_order"
            }
            ],
            "optional": true,
            "name": "event.block",
            "version": 1,
            "field": "transaction"
        },
        {
            "type": "string",
            "optional": false,
            "field": "op"
        },
        {
            "type": "int64",
            "optional": true,
            "field": "ts_ms"
        },
        {
            "type": "int64",
            "optional": true,
            "field": "ts_us"
        },
        {
            "type": "int64",
            "optional": true,
            "field": "ts_ns"
        }
        ],
        "optional": false,
        "name": "mysql.inventory.customers.Envelope",
        "version": 2
    },
    "payload": {
        "before": {
        "id": 1001,
        "first_name": "Sally",
        "last_name": "Thomas",
        "email": "sally.thomas@acme.com"
        },
        "after": {
        "id": 1001,
        "first_name": "Sally Marie",
        "last_name": "Thomas",
        "email": "sally.thomas@acme.com"
        },
        "source": {
        "version": "3.1.0.Final",
        "connector": "mysql",
        "name": "mysql",
        "ts_ms": 1751201044000,
        "snapshot": "false",
        "db": "inventory",
        "sequence": null,
        "ts_us": 1751201044000000,
        "ts_ns": 1751201044000000000,
        "table": "customers",
        "server_id": 1,
        "gtid": null,
        "file": "binlog.000002",
        "pos": 401,
        "row": 0,
        "thread": 14,
        "query": null
        },
        "transaction": null,
        "op": "u",
        "ts_ms": 1751201044907,
        "ts_us": 1751201044907793,
        "ts_ns": 1751201044907793970
    }
    }
    ```




## References

- [Deploying Debezium on Kubernetes | Debezium Documentation](https://debezium.io/documentation//reference/stable/operations/kubernetes.html)
- [Deploying and Managing | Strimzi Documentation](https://strimzi.io/docs/operators/latest/deploying)
- [Using the Iceberg framework in AWS Glue | AWS](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-format-iceberg.html)
- [Iceberg Kafka Connector | Iceberg](https://iceberg.apache.org/docs/latest/kafka-connect/)