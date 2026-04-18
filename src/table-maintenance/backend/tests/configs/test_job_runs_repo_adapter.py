from configs import JobRunsRepoAdapter


def test_enum_values():
    assert JobRunsRepoAdapter.IN_MEMORY == "in_memory"
    assert JobRunsRepoAdapter.SQL == "sql"


def test_is_str_enum():
    assert isinstance(JobRunsRepoAdapter.IN_MEMORY, str)
    assert isinstance(JobRunsRepoAdapter.SQL, str)
