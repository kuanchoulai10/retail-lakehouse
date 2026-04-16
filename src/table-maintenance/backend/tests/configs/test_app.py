from configs import AppSettings


def test_defaults():
    s = AppSettings()
    assert s.k8s.namespace == "default"
    assert s.k8s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.k8s.image_pull_policy == "Never"
    assert s.k8s.spark_version == "4.0.0"
    assert s.k8s.service_account == "spark-operator-spark"
    assert s.k8s.driver_memory == "512m"
    assert s.k8s.executor_memory == "1g"
    assert s.k8s.executor_instances == 1


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BACKEND_K8S__NAMESPACE", "spark-jobs")
    s = AppSettings()
    assert s.k8s.namespace == "spark-jobs"
