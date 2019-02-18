import logging
from importlib import import_module

from django.apps.config import MODELS_MODULE_NAME
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from pg_partitioning.manager import _PartitionManagerBase

logger = logging.getLogger(__name__)


default_create_model_method = DatabaseSchemaEditor.create_model
default_sql_create_table = DatabaseSchemaEditor.sql_create_table


def create_model(self, model):
    meta = model._meta
    try:
        cls_module = import_module(f"{meta.app_label}.{MODELS_MODULE_NAME}")
    except ModuleNotFoundError:
        cls_module = None
    cls = getattr(cls_module, meta.object_name, None)
    partitioning = getattr(cls, "partitioning", None)
    if isinstance(partitioning, _PartitionManagerBase):
        # XXX: Monkeypatch create_model.
        logger.debug("Partitioned model detected: %s", meta.label)
        _type = partitioning.type
        key = partitioning.partition_key
        DatabaseSchemaEditor.sql_create_table = f"CREATE TABLE %(table)s (%(definition)s) PARTITION BY {_type} ({key})"
        if meta.pk.name != key:
            """The partition key must be part of the primary key,
            and currently Django does not support setting a composite primary key,
            so its properties are turned off."""
            meta.pk.primary_key = False
            logger.info("Note that PK constraints for %s has been temporarily closed.", meta.label)
    else:
        DatabaseSchemaEditor.sql_create_table = default_sql_create_table
    default_create_model_method(self, model)
    meta.pk.primary_key = True


DatabaseSchemaEditor.create_model = create_model
