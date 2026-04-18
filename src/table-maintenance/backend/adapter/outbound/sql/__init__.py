"""Shared SQL infrastructure layer.

Provides components shared by all domain-specific SQL adapters:

- ``metadata`` — Centralized SQLAlchemy MetaData instance where all table
  definitions are registered, enabling unified schema management
  (e.g. ``metadata.create_all``).
- ``build_engine`` — Creates a SQLAlchemy Engine from AppSettings database
  configuration.

Domain-specific SQL adapters (e.g. ``job/sql/``, ``job_run/sql/``) reference
the ``metadata`` and ``build_engine`` here to avoid duplicating connections
or maintaining separate metadata. In short, this is the shared kernel for the
SQL layer.
"""
