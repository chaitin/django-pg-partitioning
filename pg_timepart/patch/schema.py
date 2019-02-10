"""
Add partitioned table schema support
"""
import logging
from importlib import import_module

from django.apps.config import MODELS_MODULE_NAME
from django.db.backends.postgresql.schema import DatabaseSchemaEditor

logger = logging.getLogger(__name__)


def partitioned_column_sql(self, model, field, include_default=False):
    """
    Take a field and return its column definition.
    The field must already have had set_attributes_from_name() called.
    """
    # Get the column's type and use that as the basis of the SQL
    db_params = field.db_parameters(connection=self.connection)
    sql = db_params["type"]
    params = []
    # Check for fields that aren't actually columns (e.g. M2M)
    if sql is None:
        return None, None
    # Work out nullability
    null = field.null
    # If we were told to include a default value, do so
    include_default = include_default and not self.skip_default(field)
    if include_default:
        default_value = self.effective_default(field)
        if default_value is not None:
            if self.connection.features.requires_literal_defaults:
                # Some databases can't take defaults as a parameter (oracle)
                # If this is the case, the individual schema backend should
                # implement prepare_default
                sql += " DEFAULT %s" % self.prepare_default(default_value)
            else:
                sql += " DEFAULT %s"
                params += [default_value]
    # Oracle treats the empty string ('') as null, so coerce the null
    # option whenever '' is a possible value.
    if field.empty_strings_allowed and not field.primary_key and self.connection.features.interprets_empty_strings_as_nulls:
        null = True
    if null and not self.connection.features.implied_column_null:
        sql += " NULL"
    elif not null:
        sql += " NOT NULL"
    # [pg_timepart]
    if self.partition_key == field.column:
        # Primary key/unique outputs
        if field.primary_key:
            sql += " PRIMARY KEY"
        elif field.unique:
            sql += " UNIQUE"
            # Optionally add the tablespace if it's an implicitly indexed column
            tablespace = field.db_tablespace or model._meta.db_tablespace
            if tablespace and self.connection.features.supports_tablespaces:
                sql += " %s" % self.connection.ops.tablespace_sql(tablespace, inline=True)
    else:
        logger.debug("Skip the declaration of primary key, unique or implicitly indexed column in %s", model)
    # Return the sql
    return sql, params


def create_partitioned_model(self, model):
    """
    Create a table and any accompanying indexes or unique constraints for
    the given `model`.
    """
    # Create column SQL, add FK deferreds if needed
    column_sqls = []
    params = []
    for field in model._meta.local_fields:
        # SQL
        definition, extra_params = partitioned_column_sql(self, model, field)
        if definition is None:
            continue
        # Check constraints can go on the column SQL here
        db_params = field.db_parameters(connection=self.connection)
        if db_params["check"]:
            definition += " CHECK (%s)" % db_params["check"]
        # Autoincrement SQL (for backends with inline variant)
        col_type_suffix = field.db_type_suffix(connection=self.connection)
        if col_type_suffix:
            definition += " %s" % col_type_suffix
        params.extend(extra_params)
        # FK
        if field.remote_field and field.db_constraint:
            to_table = field.remote_field.model._meta.db_table
            to_column = field.remote_field.model._meta.get_field(field.remote_field.field_name).column
            if self.sql_create_inline_fk:
                definition += " " + self.sql_create_inline_fk % {"to_table": self.quote_name(to_table), "to_column": self.quote_name(to_column)}
            elif self.connection.features.supports_foreign_keys:
                self.deferred_sql.append(self._create_fk_sql(model, field, "_fk_%(to_table)s_%(to_column)s"))
        # Add the SQL to our big list
        column_sqls.append("%s %s" % (self.quote_name(field.column), definition))
        # Autoincrement SQL (for backends with post table definition variant)
        if field.get_internal_type() in ("AutoField", "BigAutoField"):
            autoinc_sql = self.connection.ops.autoinc_sql(model._meta.db_table, field.column)
            if autoinc_sql:
                self.deferred_sql.extend(autoinc_sql)

    # Add any unique_togethers (always deferred, as some fields might be
    # created afterwards, like geometry fields with some backends)
    for fields in model._meta.unique_together:
        columns = [model._meta.get_field(field).column for field in fields]
        self.deferred_sql.append(self._create_unique_sql(model, columns))
    # Make the table
    sql = self.sql_create_table % {"table": self.quote_name(model._meta.db_table), "definition": ", ".join(column_sqls)}
    # [pg_timepart] Add partitioned table declarative sql
    sql += f" PARTITION BY RANGE ({self.partition_key})"
    if model._meta.db_tablespace:
        tablespace_sql = self.connection.ops.tablespace_sql(model._meta.db_tablespace)
        if tablespace_sql:
            sql += " " + tablespace_sql
    # Prevent using [] as params, in the case a literal '%' is used in the definition
    self.execute(sql, params or None)

    # Add any field index and index_together's (deferred as SQLite3 _remake_table needs it)
    self.deferred_sql.extend(self._model_indexes_sql(model))

    # Make M2M tables
    for field in model._meta.local_many_to_many:
        if field.remote_field.through._meta.auto_created:
            self.create_model(field.remote_field.through)


def create_model(self, model):
    try:
        model_module = import_module(f"{model._meta.app_label}.{MODELS_MODULE_NAME}")
        model_cls = getattr(model_module, model._meta.object_name)
        self.partition_key = model_cls.partitioning.partition_key
        logger.debug("Partitioned model detected: %s", model_cls)
        create_partitioned_model(self, model)
    except (ModuleNotFoundError, AttributeError):
        origin_create_model(self, model)


origin_create_model = DatabaseSchemaEditor.create_model
DatabaseSchemaEditor.create_model = create_model
