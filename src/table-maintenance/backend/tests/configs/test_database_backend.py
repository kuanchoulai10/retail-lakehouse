from configs import DatabaseBackend


def test_enum_values():
    assert DatabaseBackend.SQLITE == "sqlite"
    assert DatabaseBackend.POSTGRES == "postgres"


def test_is_str_enum():
    assert isinstance(DatabaseBackend.SQLITE, str)
    assert isinstance(DatabaseBackend.POSTGRES, str)
