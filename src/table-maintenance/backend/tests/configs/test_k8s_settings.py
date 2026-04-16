from configs import AppSettings, K8sSettings


def test_defaults():
    s = K8sSettings()
    assert s.namespace == "default"
    assert s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.image_pull_policy == "Never"
    assert s.spark_version == "4.0.0"
    assert s.service_account == "spark-operator-spark"
    assert s.driver_memory == "512m"
    assert s.executor_memory == "1g"
    assert s.executor_instances == 1
    assert s.iceberg_jar.startswith("https://repo1.maven.org/")
    assert s.iceberg_aws_jar.startswith("https://repo1.maven.org/")


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BACKEND_K8S__NAMESPACE", "spark-jobs")
    monkeypatch.setenv("BACKEND_K8S__EXECUTOR_INSTANCES", "3")
    s = AppSettings()
    assert s.k8s.namespace == "spark-jobs"
    assert s.k8s.executor_instances == 3
