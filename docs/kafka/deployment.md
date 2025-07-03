# Deployment

![](../architecture.drawio.svg)

You can deploy Strimzi on Kubernetes 1.25 and later using one of the following methods:

- Deployment files (YAML files)
- OperatorHub.io
- Helm chart

The basic deployment path includes the following steps:

- Deploy the Strimzi Cluster Operator
- Deploy a Kafka Cluster
- Deploy a MySQL Database
- Deploy a Debezium Source Connector
    - Create a Secret for Connecting to the Database
    - Create a Debezium Kafka Connect Cluster
    - Create a Debezium Source Connector
    - Verify the Data Pipeline
- Deploy an Iceberg Sink Connector
    - Create a Secret for Connecting to AWS
    - Create an Iceberg Kafka Connect Cluster
    - Create an Iceberg Sink Connector
    - Verify the Data Pipeline


## Deploy the Strimzi Cluster Operator

Create a Kubernetes Namespace for the Strimzi Cluster Operator:

```bash
kubectl create namespace strimzi
```

Create a Kubernetes Namespace for the Kafka cluster:

```bash
kubectl create namespace kafka-cdc
```


Show the default values of the Strimzi Kafka Operator Helm chart:

```
helm show values oci://quay.io/strimzi-helm/strimzi-kafka-operator > values-default.yaml
```

Review the default values in `values-default.yaml` and modify them as needed. For example, you can set the `watchNamespaces` to the namespace where you want to deploy the Kafka cluster (`kafka-cdc` in this case):

??? info "values.yaml"

    ```yaml linenums="1" hl_lines="8 9"
    --8<-- "./kafka/values.yaml"
    ```


Install the Strimzi Cluster Operator using Helm:

```
helm install strimzi-cluster-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator -f values.yaml -n strimzi
```

```
Pulled: quay.io/strimzi-helm/strimzi-kafka-operator:0.46.1
Digest: sha256:e87ea2a03985f5dd50fee1f8706f737fa1151b86dce5021b6c0798ac8b17e27f
NAME: strimzi-cluster-operator
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

After the installation, you can verify that the Strimzi Cluster Operator is running:

```bash
helm ls -n strimzi
```

```
NAME                    	NAMESPACE	REVISION	UPDATED                             	STATUS  	HART                        	APP VERSION
strimzi-cluster-operator	strimzi  	1       	2025-06-29 17:25:49.773026 +0800 CST	deployed	trimzi-kafka-operator-0.46.1	0.46.1     
```

```bash
kubectl get all -n strimzi
```

```
NAME                                           READY   STATUS    RESTARTS   AGE
pod/strimzi-cluster-operator-74f577b78-s9n25   1/1     Running   0          108s

NAME                                           READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/strimzi-cluster-operator       1/1     1            1           108s

NAME                                                 DESIRED   CURRENT   READY   AGE
replicaset.apps/strimzi-cluster-operator-74f577b78   1         1         1       108s
```

## Deploying a Kafka Cluster

To deploy a Kafka cluster in KRaft mode, you need to create a Kafka cluster YAML file that defines the cluster configuration. Below is an example of such a file:

```yaml title="kafka-cluster.yaml"
--8<-- "./kafka/kafka-cluster.yaml"
```

Kafka 4.0 開始預設支援 KRaft；`metadataVersion`，IV 代表 Incompatible Version，也就是: Kafka 叢集 metadata 結構出現重大變更，跟舊版不相容，所以需要你明確地指定升級。

### KRaft Mode

KRaft 模式是 Kafka 的一種新架構，取代了傳統的 ZooKeeper。它讓 Kafka broker 自己管理元資料（metadata），不再需要依賴外部的 ZooKeeper 叢集。這樣做的好處包括：

- 簡化部署：不需要額外安裝和維護 ZooKeeper。
- 提升性能：減少了跨叢集的網路延遲。
- 增強可靠性：減少了單點故障的風險。

要在 Kafka Cluster 中啟用 KRaft 模式，你需要替 `strimzi.io/node-pools` 和 `strimzi.io/kraft` 這兩個註解加上 `enabled`。這樣 Strimzi 就會知道你要使用 KRaft 模式。


不僅如此，在使用 KRaft 模式時，Strimzi 把 Kafka broker 的節點角色（如 controller、broker）和儲存設定獨立出來，用 KafkaNodePool 這個 CRD 來描述。這讓你可以：

- 把不同角色（controller-only、broker-only、dual-role）分配到不同實體節點
- 更細緻地分配儲存資源（像是磁碟大小、是否共用 metadata）

這段定義了一個名叫 dual-role 的 `KafkaNodePool`，會掛在名為 `kafka-cluster` 的 Kafka Cluster之下。也就是說，這組節點是 `kafka-cluster` Kafka cluster 的一部分。我們希望這個節點池中有 3 個副本（replica），也就是說，會有 3 台 Pod 被建立，這裡指定每個節點同時扮演：

- Kafka controller（負責元資料管理，取代原來 ZooKeeper 的角色）
- Kafka broker（接收與傳送訊息給 producer/consumer）

這叫做 dual-role（雙重角色）部署，在小型叢集中很常見，可節省資源。

- 使用 JBOD（Just a Bunch Of Disks）：支持多塊磁碟配置（可用來分開 log、metadata）
- 設定了一塊名為 id: 0 的 volume：
    - 是 persistent-claim，表示會動態建立 PVC（PersistentVolumeClaim）
    - 大小為 100Gi
    - deleteClaim: false 表示刪除 Pod 時不會順便刪掉 PVC（避免資料遺失）
    - kraftMetadata: shared：這是 KRaft 專屬欄位，表示這塊磁碟同時儲存：
    - Kafka log（一般訊息）
    - Kafka metadata（controller quorum data）

什麼情況會用這種設計？這種設定很適合：

- 中小型叢集（3 台 broker）
- 想減少部署複雜度（不想分開 controller 與 broker）
- 想善用資源、少開機器
- 正式環境中需要 KRaft 模式（無 ZooKeeper）

這份 KafkaNodePool 設定建立了 3 台「同時扮演 controller 和 broker 的 Kafka 節點」，每台使用一塊 100Gi 的持久化磁碟，來存放訊息與 metadata。

### Listener

Kafka 中的 listener 是用來定義 Kafka broker 如何接收 client（如 producer、consumer、Kafka Connect 等）連線 的機制。可以把它想成是「Kafka 對外開的門」，每個 listener 設定會影響：

- 用什麼協定連線（PLAINTEXT、SSL、SASL、等）
- 是否允許 TLS 加密
- 可以從哪裡連進來（內部？外部？）
- 用哪個 Port 提供服務

定義兩種內部連線方式。

第一種的意思是：「我要開一個 listener，名稱叫 plain，監聽在 port 9092，只給叢集裡面的服務使用（internal），不啟用加密（TLS）。」也就是說，這是一個走明文的內部通訊通道，通常會給開發時用，或是叢集內部 service（例如 Kafka Connect）使用。

第二種的意思是：「再開一個叫 tls 的 listener，在 port 9093 上，只提供叢集內部使用，但這次要 啟用 TLS 加密。」也就是說，這是一個比較安全的內部通訊通道，適合用在需要機密性或驗證的情境（例如跨 namespace 使用、或內部有資料敏感性時）。

這樣設的目的是讓你：

- 可以選擇 快速但沒加密的通道（plain）來降低資源消耗
- 或選擇 安全但略慢的通道（tls）來保護資料

某些 internal components（如 Kafka Connect、MirrorMaker）甚至可以根據用途選擇連不同的 listener。

### Configurations

`offsets.topic.replication.factor: 3`

: Kafka 內部會用一個叫 `__consumer_offsets` 的 topic 來儲存 每個 consumer 的讀取進度（offset）。這行設定告訴 Kafka：「請把這個 offsets topic 的每筆資料，都備份三份，分散存放在三個不同的 broker 上。」這樣做的好處是：就算壞掉一台 broker，也不會丟失消費者的讀取進度。


`transaction.state.log.replication.factor: 3`

: 當 Kafka 用於 交易（transactional）訊息傳遞，它會在內部維護一個叫做 `__transaction_state` 的特殊 topic。這個設定的意思是：「請將每個 transaction 的狀態，也備份三份，保存在三個 broker 上。」這樣即使其中一台 broker 損壞，Kafka 也能保證 exactly-once delivery（恰好一次） 的可靠性。


`transaction.state.log.min.isr: 2`

： ISR 是 In-Sync Replicas 的縮寫，意思是「目前跟 leader 保持同步的副本」。這行設定的意思是：「在寫入 transaction 狀態時，至少要有兩份副本是同步的，Kafka 才會認為寫入成功。」這是一種 強一致性保證，確保寫進 Kafka 的交易資料，不會只存在一份而造成風險。

`default.replication.factor: 3`

: 這是 Kafka 在 建立新 topic 時的預設副本數量。這行的意思是：「如果用戶端沒有特別指定 topic 要有幾個副本，那就自動幫他設成三個副本。」這提供一種「預設的高可用」，防止開發者忘了設定而導致資料沒備份。

`min.insync.replicas: 2`

: 這個設定決定了 producer 在寫入資料時，Kafka 最少需要幾個副本同步成功，才會回應 producer 說『OK，你寫進來了』。這裡設定成 2，代表：「每次 producer 寫入訊息，至少要有兩個 broker 成功同步，Kafka 才會回應 ACK。」這樣即使有一台 broker 掛掉，資料還有另一份備份在，提升寫入的資料安全性。

這五個設定合起來，是在對 Kafka 說：「我想要一個高度容錯、高可用、強一致性的 Kafka 環境，所以不論是 consumer offset、交易資料、或普通訊息，我都要求它們至少要有三份備份，而且要有兩份成功同步才算寫入成功。」

After creating the YAML file and the namespace, you can deploy the Kafka cluster using the following command:

```bash
kubectl create -f kafka-cluster.yaml -n kafka-cdc
```

```
kafka.kafka.strimzi.io/kafka-cluster created
kafkanodepool.kafka.strimzi.io/dual-role created
```

Check the status of the Kafka cluster:

```bash
kubectl get all -n kafka-cdc
```

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

## Deploy a MySQL Database

```yaml title="db.yaml"
--8<-- "./kafka/db.yaml"
```

```bash
kubectl apply -f db.yaml -n kafka-cdc
```

```
service/mysql created
deployment.apps/mysql created
```

```bash
kubectl get all -n kafka-cdc
```

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


## Deploy a Debezium Source Connector

### Create Secrets for the Database

```yaml title="debezium-secret.yaml" linenums="1" hl_lines="4"
--8<-- "./kafka/debezium-secret.yaml"
```

```yaml title="debezium-role.yaml" linenums="1" hl_lines="4 9"
--8<-- "./kafka/debezium-role.yaml"
```

```yaml title="debezium-role-binding.yaml" linenums="1" hl_lines="4 8 12"
--8<-- "./kafka/debezium-role-binding.yaml"
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

### Create a Debezium Kafka Connect Cluster

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

10.103.211.36
```

```yaml title="debezium-connect-cluster.yaml"
--8<-- "./kafka/debezium-connect-cluster.yaml"
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


### Create a Debezium Source Connector

```yaml title="debezium-connector.yaml"
--8<-- "./kafka/debezium-connector.yaml"
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
### Verify the Data Pipeline

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



## Deploy an Iceberg Sink Connector

### Create a Secret for Connecting to AWS

```yaml title="iceberg-secret.yaml" linenums="1" hl_lines="4 5"
--8<-- "./kafka/iceberg-secret.yaml"
```

```bash
kubectl apply -f iceberg-secret.yaml -n kafka-cdc
```

### Create an Iceberg Kafka Connect Cluster

```yaml title="iceberg-connect-cluster.yaml" linenums="1" hl_lines="4 5"
--8<-- "./kafka/iceberg-connect-cluster.yaml"
```

```bash
kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc
```

```bash
kubectl get all -n kafka-cdc

NAME                                                 READY   STATUS    RESTARTS   AGE
pod/debezium-connect-cluster-connect-0               1/1     Running   0          8m15s
{==pod/iceberg-connect-cluster-connect-0==}                1/1     Running   0          73s
pod/kafka-cluster-dual-role-0                        1/1     Running   0          14m
pod/kafka-cluster-dual-role-1                        1/1     Running   0          14m
pod/kafka-cluster-dual-role-2                        1/1     Running   0          14m
pod/kafka-cluster-entity-operator-598bb8df8b-q2d4x   2/2     Running   0          13m
pod/mysql-6b84fd947d-kpdk4                           1/1     Running   0          12m

NAME                                           TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                                        AGE
service/debezium-connect-cluster-connect       ClusterIP   None             <none>        8083/TCP                                       8m15s
service/debezium-connect-cluster-connect-api   ClusterIP   10.103.185.205   <none>        8083/TCP                                       8m15s
{==service/iceberg-connect-cluster-connect==}        ClusterIP   None             <none>        8083/TCP                                       73s
{==service/iceberg-connect-cluster-connect-api==}    ClusterIP   10.102.45.63     <none>        8083/TCP                                       73s
service/kafka-cluster-kafka-bootstrap          ClusterIP   10.105.98.134    <none>        9091/TCP,9092/TCP,9093/TCP                     14m
service/kafka-cluster-kafka-brokers            ClusterIP   None             <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   14m
service/mysql                                  ClusterIP   None             <none>        3306/TCP                                       12m

NAME                                            READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/kafka-cluster-entity-operator   1/1     1            1           13m
deployment.apps/mysql                           1/1     1            1           12m

NAME                                                       DESIRED   CURRENT   READY   AGE
replicaset.apps/kafka-cluster-entity-operator-598bb8df8b   1         1         1       13m
replicaset.apps/mysql-6b84fd947d                           1         1         1       12m
```

### Create an Iceberg Sink Connector

```yaml title="iceberg-connector.yaml" linenums="1" hl_lines="4 5"
--8<-- "./kafka/iceberg-connector.yaml"
```

```bash
kubectl apply -f iceberg-connector.yaml -n kafka-cdc
```

```bash
kubectl get kafkaconnector -n kafka-cdc

NAME                 CLUSTER                    CONNECTOR CLASS                                   MAX TASKS   READY
debezium-connector   debezium-connect-cluster   io.debezium.connector.mysql.MySqlConnector        1           True
iceberg-connector    iceberg-connect-cluster    org.apache.iceberg.connect.IcebergSinkConnector   1           True
```

### Verify the Data Pipeline

```bash
kubectl exec -n kafka-cdc -it mysql-6b84fd947d-9g9lt -- mysql -uroot -pdebezium
```

```bash
sql> use inventory;
sql> INSERT INTO orders (order_date, purchaser, quantity, product_id)
VALUES ('2016-03-01', 1004, 3, 108);
```

#### Schema Evolution

```
mysql> ALTER TABLE orders ADD COLUMN shipping_address TEXT DEFAULT NULL;
Query OK, 0 rows affected (0.30 sec)
Records: 0  Duplicates: 0  Warnings: 0
```

```
mysql> describe orders;
+------------------+------+------+-----+---------+----------------+
| Field            | Type | Null | Key | Default | Extra          |
+------------------+------+------+-----+---------+----------------+
| order_number     | int  | NO   | PRI | NULL    | auto_increment |
| order_date       | date | NO   |     | NULL    |                |
| purchaser        | int  | NO   | MUL | NULL    |                |
| quantity         | int  | NO   |     | NULL    |                |
| product_id       | int  | NO   | MUL | NULL    |                |
| shipping_address | text | YES  |     | NULL    |                |
+------------------+------+------+-----+---------+----------------+
6 rows in set (0.05 sec)
```

```
mysql> select * from orders;
+--------------+------------+-----------+----------+------------+------------------+
| order_number | order_date | purchaser | quantity | product_id | shipping_address |
+--------------+------------+-----------+----------+------------+------------------+
|        10001 | 2016-01-16 |      1001 |        1 |        102 | NULL             |
|        10002 | 2016-01-17 |      1002 |        2 |        105 | NULL             |
|        10003 | 2016-02-19 |      1002 |        2 |        106 | NULL             |
|        10004 | 2016-02-21 |      1003 |        1 |        107 | NULL             |
|        10005 | 2016-03-01 |      1004 |        3 |        108 | NULL             |
+--------------+------------+-----------+----------+------------+------------------+
5 rows in set (0.00 sec)
```


```
INSERT INTO orders (order_date, purchaser, quantity, product_id, shipping_address)
VALUES ('2016-03-05', 1005, 2, 109, '123 Main Street, Taipei City');
Query OK, 1 row affected (0.04 sec)
```

```
mysql> select * from orders;
+--------------+------------+-----------+----------+------------+------------------------------+
| order_number | order_date | purchaser | quantity | product_id | shipping_address             |
+--------------+------------+-----------+----------+------------+------------------------------+
|        10001 | 2016-01-16 |      1001 |        1 |        102 | NULL                         |
|        10002 | 2016-01-17 |      1002 |        2 |        105 | NULL                         |
|        10003 | 2016-02-19 |      1002 |        2 |        106 | NULL                         |
|        10004 | 2016-02-21 |      1003 |        1 |        107 | NULL                         |
|        10005 | 2016-03-01 |      1004 |        3 |        108 | NULL                         |
|        10006 | 2016-03-05 |      1005 |        2 |        109 | 123 Main Street, Taipei City |
+--------------+------------+-----------+----------+------------+------------------------------+
6 rows in set (0.02 sec)
```

## References

- [Deploying Debezium on Kubernetes | Debezium Documentation](https://debezium.io/documentation//reference/stable/operations/kubernetes.html)
- [Deploying and Managing | Strimzi Documentation](https://strimzi.io/docs/operators/latest/deploying)