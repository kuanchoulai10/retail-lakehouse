from configs import JobRunExecutorAdapter


def test_enum_values():
    assert JobRunExecutorAdapter.IN_MEMORY == "in_memory"
    assert JobRunExecutorAdapter.K8S == "k8s"


def test_is_str_enum():
    assert isinstance(JobRunExecutorAdapter.IN_MEMORY, str)
    assert isinstance(JobRunExecutorAdapter.K8S, str)
