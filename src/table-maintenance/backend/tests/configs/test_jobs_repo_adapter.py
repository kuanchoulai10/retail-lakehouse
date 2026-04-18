from configs import JobsRepoAdapter


def test_enum_values():
    assert JobsRepoAdapter.IN_MEMORY == "in_memory"
    assert JobsRepoAdapter.SQL == "sql"


def test_is_str_enum():
    assert isinstance(JobsRepoAdapter.IN_MEMORY, str)
    assert isinstance(JobsRepoAdapter.SQL, str)
