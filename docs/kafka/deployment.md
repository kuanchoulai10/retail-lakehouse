# Deployment

You can deploy Strimzi on Kubernetes 1.25 and later using one of the following methods:

- Deployment files (YAML files)
- OperatorHub.io
- Helm chart

The basic deployment path includes the following steps:

- Deploy the Strimzi Cluster Operator
- Deploy the Kafka cluster
- Deploy a database (MySQL or PostgreSQL)
- Create decrets for the database
- Deploy a Debezium Connector

## Deploy the Strimzi Cluster Operator

Create a Kubernetes Namespace for the Strimzi Cluster Operator:

```bash
kubectl create namespace strimzi
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

After the installation, you can verify that the Strimzi Cluster Operator is running:

```bash
helm ls -n strimzi
```

```
NAME                    	NAMESPACE	REVISION	UPDATED                             	STATUS  	CHART                        	APP VERSION
strimzi-cluster-operator	strimzi  	1       	2025-06-25 22:24:51.172738 +0800 CST	deployed	strimzi-kafka-operator-0.46.1	0.46.1     
```

```bash
kubectl get all -n strimzi
```

```
NAME                                           READY   STATUS    RESTARTS   AGE
pod/strimzi-cluster-operator-5dd9cc85d-mwdn9   1/1     Running   0          4m32s

NAME                                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/strimzi-cluster-operator   1/1     1            1           4m32s

NAME                                                 DESIRED   CURRENT   READY   AGE
replicaset.apps/strimzi-cluster-operator-5dd9cc85d   1         1         1       4m32s
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

這段定義了一個名叫 dual-role 的 `KafkaNodePool`，會掛在名為 `debezium-cluster` 的 Kafka Cluster之下。也就是說，這組節點是 `debezium-cluster` Kafka cluster 的一部分。我們希望這個節點池中有 3 個副本（replica），也就是說，會有 3 台 Pod 被建立，這裡指定每個節點同時扮演：

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

- `offsets.topic.replication.factor: 3`:Kafka 內部會用一個叫 `__consumer_offsets` 的 topic 來儲存 每個 consumer 的讀取進度（offset）。這行設定告訴 Kafka：「請把這個 offsets topic 的每筆資料，都備份三份，分散存放在三個不同的 broker 上。」這樣做的好處是：就算壞掉一台 broker，也不會丟失消費者的讀取進度。
- `transaction.state.log.replication.factor: 3`: 當 Kafka 用於 交易（transactional）訊息傳遞，它會在內部維護一個叫做 `__transaction_state` 的特殊 topic。這個設定的意思是：「請將每個 transaction 的狀態，也備份三份，保存在三個 broker 上。」這樣即使其中一台 broker 損壞，Kafka 也能保證 exactly-once delivery（恰好一次） 的可靠性。
- `transaction.state.log.min.isr: 2`: ISR 是 In-Sync Replicas 的縮寫，意思是「目前跟 leader 保持同步的副本」。這行設定的意思是：「在寫入 transaction 狀態時，至少要有兩份副本是同步的，Kafka 才會認為寫入成功。」這是一種 強一致性保證，確保寫進 Kafka 的交易資料，不會只存在一份而造成風險。
- `default.replication.factor: 3`: 這是 Kafka 在 建立新 topic 時的預設副本數量。這行的意思是：「如果用戶端沒有特別指定 topic 要有幾個副本，那就自動幫他設成三個副本。」這提供一種「預設的高可用」，防止開發者忘了設定而導致資料沒備份。
- `min.insync.replicas: 2`: 這個設定決定了 producer 在寫入資料時，Kafka 最少需要幾個副本同步成功，才會回應 producer 說『OK，你寫進來了』。這裡設定成 2，代表：「每次 producer 寫入訊息，至少要有兩個 broker 成功同步，Kafka 才會回應 ACK。」這樣即使有一台 broker 掛掉，資料還有另一份備份在，提升寫入的資料安全性。

這五個設定合起來，是在對 Kafka 說：「我想要一個高度容錯、高可用、強一致性的 Kafka 環境，所以不論是 consumer offset、交易資料、或普通訊息，我都要求它們至少要有三份備份，而且要有兩份成功同步才算寫入成功。」


Create a Kubernetes Namespace for the Kafka cluster:

```bash
kubectl create namespace kafka-cdc
```

After creating the YAML file and the namespace, you can deploy the Kafka cluster using the following command:

```bash
kubectl create -f kafka-cluster.yaml -n kafka-cdc
```

```
kafkanodepool.kafka.strimzi.io/dual-role created
kafka.kafka.strimzi.io/my-cluster created
```

Check the status of the Kafka cluster:

```bash
kubectl get all -n kafka-cdc
```

```
NAME                                              READY   STATUS    RESTARTS   AGE
pod/my-cluster-dual-role-0                        1/1     Running   0          2m19s
pod/my-cluster-dual-role-1                        1/1     Running   0          2m19s
pod/my-cluster-dual-role-2                        1/1     Running   0          2m19s
pod/my-cluster-entity-operator-674f9db8bf-sr8kk   2/2     Running   0          36s

NAME                                 TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                                        AGE
service/my-cluster-kafka-bootstrap   ClusterIP   10.111.119.151   <none>        9091/TCP,9092/TCP,9093/TCP                     2m20s
service/my-cluster-kafka-brokers     ClusterIP   None             <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   2m20s

NAME                                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/my-cluster-entity-operator   1/1     1            1           36s

NAME                                                    DESIRED   CURRENT   READY   AGE
replicaset.apps/my-cluster-entity-operator-674f9db8bf   1         1         1       36s
```

## Deploy a Database

```yaml title="db.yaml"
--8<-- "./kafka/db.yaml"
```

```bash
kubectl apply -f db.yaml -n kafka-cdc
```

## Create Secrets for the Database

```yaml title="debezium-secret.yaml"
--8<-- "./kafka/debezium-secret.yaml"
```

```bash
kubectl apply -f debezium-secret.yaml -n kafka-cdc
```


```yaml title="debezium-role.yaml"
--8<-- "./kafka/debezium-role.yaml"
```

```bash
kubectl apply -f debezium-role.yaml -n kafka-cdc
```

```yaml title="debezium-role-binding.yaml"
--8<-- "./kafka/debezium-role-binding.yaml"
```

```bash
kubectl apply -f debezium-role-binding.yaml -n kafka-cdc
```

## Deploy a Debezium Connector

To deploy a Debezium connector, you need to deploy a Kafka Connect cluster with the required connector plug-in(s), before instantiating the actual connector itself.

### Creating a Kafka Connect Cluster

```yaml title="debezium-kafka-connect.yaml"
--8<-- "./kafka/debezium-kafka-connect.yaml"
```

```bash
kubectl apply -f debezium-kafka-connect.yaml -n kafka-cdc
```


### Creating a Debezium Connector

```yaml title="debezium-kafka-connector.yaml"
--8<-- "./kafka/debezium-kafka-connector.yaml"
```

```bash
kubectl apply -f debezium-kafka-connector.yaml -n kafka-cdc
```

## Verify the Debezium Connector

```bash
kubectl run -n debezium-example -it --rm --image=quay.io/debezium/tooling:1.2  --restart=Never watcher -- kcat -b debezium-cluster-kafka-bootstrap:9092 -C -o beginning -t mysql.inventory.customers
```

```bash
kubectl run -n debezium-example -it --rm --image=mysql:8.2 --restart=Never --env MYSQL_ROOT_PASSWORD=debezium mysqlterm -- mysql -hmysql -P3306 -uroot -pdebezium
```

```bash
sql> update customers set first_name="Sally Marie" where id=1001;
```


## References

- [Deploying Debezium on Kubernetes | Debezium Documentation](https://debezium.io/documentation//reference/stable/operations/kubernetes.html)
- [Deploying and Managing | Strimzi Documentation](https://strimzi.io/docs/operators/latest/deploying)