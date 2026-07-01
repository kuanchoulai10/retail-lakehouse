# 22-polaris-events

Deploys the pipeline that turns Polaris table commit events into Kafka messages.

- `OpenTelemetryCollector` `polaris-events` in namespace `polaris` receives
  OTLP logs from Polaris on port 4317 and exports them to Kafka.
- `KafkaTopic` `polaris.table.commits` in namespace `kafka-cdc`
  (1 partition, 7-day retention) receives events keyed by the
  fully-qualified table identifier.

Depends on wave 20 (`20-kafka-cluster`) and wave 21 (`21-polaris`).

## Deploy

    KUBE_CONTEXT=retail-lakehouse ./bootstrap.sh
    KUBE_CONTEXT=retail-lakehouse ./validate.sh

## Consume events

    kubectl exec -n kafka-cdc kafka-cluster-dual-role-0 -- \
      bin/kafka-console-consumer.sh \
        --bootstrap-server localhost:9092 \
        --topic polaris.table.commits \
        --from-beginning \
        --property print.key=true \
        --property key.separator=' | '
