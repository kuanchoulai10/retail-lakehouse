#!/bin/bash

set -e

helm repo add strimzi https://strimzi.io/charts/

kubectl create namespace strimzi
kubectl create namespace kafka-cdc
helm install strimzi-cluster-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator -f values.yaml -n strimzi --version 0.46.1


kubectl apply -f kafka-cluster.yaml -n kafka-cdc
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=kafka -n kafka-cdc --timeout=1200s


kubectl apply -f db.yaml -n kafka-cdc
kubectl wait --for=condition=Ready pod -l app=mysql -n kafka-cdc --timeout=1200s


kubectl apply -f debezium-secret.yaml
kubectl apply -f debezium-role.yaml
kubectl apply -f debezium-role-binding.yaml
kubectl apply -f debezium-connect-cluster.yaml -n kafka-cdc
kubectl wait --for=condition=Ready pod -l strimzi.io/name=debezium-connect-cluster-connect -n kafka-cdc --timeout=1200s
kubectl apply -f debezium-connector.yaml -n kafka-cdc
kubectl wait --for=condition=Ready pod -l strimzi.io/kind=KafkaConnector -n kafka-cdc --timeout=1200s

# kubectl run kafka-topics-cli \
#   -n kafka-cdc \
#   -it --rm \
#   --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 \
#   --restart=Never -- \
#   bin/kafka-topics.sh \
#     --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
#     --list


# kubectl run kafka-cli \
#   -n kafka-cdc \
#   -it --rm \
#   --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 \
#   --restart=Never -- \
#   bin/kafka-console-consumer.sh \
#     --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
#     --topic mysql.inventory.customers \
#     --partition 0
#     --offset -10
#     --max-messages 10

# kubectl exec -n kafka-cdc -it mysql-6b84fd947d-9g9lt -- mysql -uroot -pdebezium

# use inventory;
# update customers set first_name="Sally Marie" where id=1001;

# kubectl apply -f iceberg-secret.yaml -n kafka-cdc
# kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc
# kubectl apply -f iceberg-connector.yaml -n kafka-cdc
