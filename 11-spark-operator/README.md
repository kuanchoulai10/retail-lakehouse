# Spark Operator

Deploys the Kubeflow Spark Operator via Helm. The operator manages Apache Spark applications on Kubernetes by translating SparkApplication custom resources into driver and executor pods. It supports one-time and scheduled Spark jobs.

## Deployed Resources

```
Namespace: spark-operator
├── spark-operator-controller            (Deployment)
└── spark-operator-webhook               (Deployment)
```

## Namespaces

- `spark-operator`

## Pods

| Pod | Purpose |
|-----|---------|
| `spark-operator-controller` | Reconciles SparkApplication resources into driver and executor pods |
| `spark-operator-webhook` | Mutates SparkApplication pods for volume mounts and configs |

## CRDs

| CRD | Purpose |
|-----|---------|
| `sparkapplications.sparkoperator.k8s.io` | Declares a one-time Spark job |
| `scheduledsparkapplications.sparkoperator.k8s.io` | Declares a cron-scheduled Spark job |
| `sparkconnects.sparkoperator.k8s.io` | Declares a long-running Spark Connect server |
