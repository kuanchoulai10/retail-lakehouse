#!/bin/bash

set -e

helm repo add strimzi https://strimzi.io/charts/

# Deploy Strimzi Cluster Operator
kubectl create namespace strimzi
kubectl create namespace kafka-cdc
helm install strimzi-cluster-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator -f values.yaml -n strimzi --version 0.46.1
sleep 5
kubectl wait --for=condition=Ready pod -l name=strimzi-cluster-operator -n strimzi --timeout=1200s

# Deploy Kafka cluster using Strimzi
kubectl apply -f kafka-cluster.yaml -n kafka-cdc
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=kafka -n kafka-cdc --timeout=1200s
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=entity-operator -n kafka-cdc --timeout=1200s

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



# 查看 minikube registry IP
# kubectl get svc registry -o jsonpath='{.spec.clusterIP}' -n kube-system



# Observe the status of the Debezium Connect Cluster
# kubectl logs pod/debezium-connect-cluster-connect-0 -n kafka-cdc
# kubectl describe pod/debezium-connect-cluster-connect-0 -n kafka-cdc
# kubectl get pods -n kafka-cdc


# 查看 minikube registry 配置
# cat ~/.minikube/profiles/<profile_name>/config.json | jq . | grep Insecure -A10 -B10


# 查看 minikube registry images list
# kubectl port-forward --namespace kube-system service/registry 5000:80
# ssh local
# curl http://localhost:5000/v2/_catalog
# curl http://localhost:5000/v2/debezium-mysql-connector/tags/list




# kubectl exec -n kafka-cdc -it mysql-6b84fd947d-9g9lt -- mysql -uroot -pdebezium

# use inventory;
# update customers set first_name="Sally Marie" where id=1001;

kubectl apply -f iceberg-secret.yaml -n kafka-cdc
kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc
kubectl apply -f iceberg-connector.yaml -n kafka-cdc
