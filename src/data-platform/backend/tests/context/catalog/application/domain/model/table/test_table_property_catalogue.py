"""Test the catalogue of known Iceberg table properties and the values it is built from."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.catalog.application.domain.model.table import (
    TablePropertyCatalogue,
    TablePropertyDefinition,
    iceberg_table_property_catalogue,
)

CATALOGUE = iceberg_table_property_catalogue()


def _definition(key: str = "write.format.default", **changes: object) -> TablePropertyDefinition:
    fields: dict[str, object] = {
        "key": key,
        "iceberg_default": "parquet",
        "description": "File format of new data files.",
        "resettable": True,
        "written_on_create": False,
    }
    fields.update(changes)
    return TablePropertyDefinition(**fields)


def test_catalogue_pins_the_iceberg_version_the_platform_runs():
    """The defaults are those of Iceberg 1.10.1, the version of the Spark runtime and Polaris 1.8.0."""
    assert CATALOGUE.iceberg_version == "1.10.1"


@pytest.mark.parametrize("definition", CATALOGUE.definitions, ids=lambda d: d.key)
def test_every_entry_is_well_formed(definition: TablePropertyDefinition):
    """Every entry has a dotted or dashed key without spaces, a one-line description and a text default or none."""
    assert definition.key == definition.key.strip()
    assert " " not in definition.key
    assert definition.description.strip()
    assert "\n" not in definition.description
    assert definition.iceberg_default is None or isinstance(definition.iceberg_default, str)


def test_keys_are_unique():
    """No key appears twice."""
    keys = [d.key for d in CATALOGUE.definitions]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("key", "default"),
    [
        ("format-version", "2"),
        ("write.format.default", "parquet"),
        ("write.target-file-size-bytes", "536870912"),
        ("write.distribution-mode", None),
        ("write.parquet.compression-codec", "zstd"),
        ("write.metadata.delete-after-commit.enabled", "false"),
        ("write.metadata.previous-versions-max", "100"),
        ("write.object-storage.enabled", "false"),
        ("commit.retry.num-retries", "4"),
        ("commit.manifest-merge.enabled", "true"),
        ("commit.manifest.min-count-to-merge", "100"),
        ("history.expire.max-snapshot-age-ms", "432000000"),
        ("history.expire.min-snapshots-to-keep", "1"),
        ("history.expire.max-ref-age-ms", "9223372036854775807"),
        ("read.split.target-size", "134217728"),
    ],
)
def test_covers_the_commonly_used_properties_with_their_iceberg_defaults(key: str, default: str | None):
    """The common write, commit, history, read and format properties are known with Iceberg 1.10.1's default."""
    definition = CATALOGUE.definition_of(key)
    assert definition is not None
    assert definition.iceberg_default == default


def test_format_version_is_not_resettable():
    """Format version is fixed when the table is created and can only be upgraded, never removed."""
    definition = CATALOGUE.definition_of("format-version")
    assert definition is not None
    assert definition.resettable is False


def test_gc_enabled_is_not_resettable():
    """Resetting gc.enabled to true would let maintenance delete files a table registered over shared files."""
    definition = CATALOGUE.definition_of("gc.enabled")
    assert definition is not None
    assert definition.resettable is False


def test_parquet_compression_is_written_when_a_table_is_created():
    """Iceberg writes zstd on every new table; an absent key means the legacy gzip, so a reset writes zstd."""
    definition = CATALOGUE.definition_of("write.parquet.compression-codec")
    assert definition is not None
    assert definition.written_on_create is True
    others = [d.key for d in CATALOGUE.definitions if d.written_on_create and d.key != definition.key]
    assert others == []


def test_unknown_key_has_no_definition():
    """A custom key is not in the catalogue."""
    assert CATALOGUE.definition_of("owner") is None


def test_definition_refuses_a_blank_key_or_description():
    """A key and a description are required text."""
    with pytest.raises(ValidationError):
        _definition(" ")
    with pytest.raises(ValidationError):
        _definition(description=" ")


def test_definition_refuses_a_key_with_whitespace():
    """A property key holds no whitespace."""
    with pytest.raises(ValidationError):
        _definition("write format")


def test_not_resettable_definition_is_never_written_on_create():
    """A key Iceberg writes on create is restored by a reset, so it cannot also refuse a reset."""
    with pytest.raises(ValidationError):
        _definition(resettable=False, written_on_create=True)


def test_written_on_create_needs_a_default():
    """A reset writes the default, so a key written on create has one."""
    with pytest.raises(ValidationError):
        _definition(iceberg_default=None, written_on_create=True)


def test_catalogue_refuses_duplicate_keys():
    """Two entries with one key are refused."""
    with pytest.raises(ValidationError):
        TablePropertyCatalogue(iceberg_version="1.10.1", definitions=(_definition(), _definition()))


def test_catalogue_refuses_a_blank_version():
    """The Iceberg version the defaults belong to is required."""
    with pytest.raises(ValidationError):
        TablePropertyCatalogue(iceberg_version=" ", definitions=(_definition(),))
