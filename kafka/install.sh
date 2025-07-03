kubectl create namespace strimzi
kubectl create namespace kafka-cdc
helm install strimzi-cluster-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator -f values.yaml -n strimzi

kubectl apply -f kafka-cluster.yaml -n kafka-cdc

kubectl apply -f db.yaml -n kafka-cdc

kubectl apply -f debezium-secret.yaml
kubectl apply -f debezium-role.yaml
kubectl apply -f debezium-role-binding.yaml
kubectl apply -f debezium-connect-cluster.yaml -n kafka-cdc
kubectl apply -f debezium-connector.yaml -n kafka-cdc

kubectl apply -f iceberg-secret.yaml -n kafka-cdc
kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc
kubectl apply -f iceberg-connector.yaml -n kafka-cdc
