#!/bin/bash

set -e

cd ~/Projects/retail-lakehouse/mysql
kubectl apply -f mysql.yaml -n kafka-cdc
sleep 5
kubectl wait --for=condition=Ready pod -l app=mysql -n kafka-cdc --timeout=1200s
