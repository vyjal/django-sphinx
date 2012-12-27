# coding: utf-8

import django
from django.conf import settings
from django.template import Context

from django.db import models
from django.db.models.fields import *
from django.contrib.contenttypes.models import ContentType

# import djangosphinx.apis.current as sphinxapi
from sphinxapi import sphinxapi
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import select_template

__all__ = ('generate_config_for_model', 'generate_config_for_models', 'generate_sphinx_config')

DJANGO_MINOR_VERSION = float(".".join([str(django.VERSION[0]), str(django.VERSION[1])]))

DOCUMENT_ID_SHIFT = 24

def _get_database_engine():
    if DJANGO_MINOR_VERSION < 1.2:
        if settings.DATABASE_ENGINE == 'mysql':
            return settings.DATABASE_ENGINE
        elif settings.DATABASE_ENGINE.startswith('postgresql'):
            return 'pgsql'
    else:
        if 'mysql' in settings.DATABASES['default']['ENGINE']:
            return 'mysql'
        elif 'postgresql' in settings.DATABASES['default']['ENGINE']:
            return 'pgsql'
    raise ValueError("Only MySQL and PostgreSQL engines are supported by Sphinx.")


def _get_template(name, index=None):
    paths = [
        'sphinx/api%s' % sphinxapi.VER_COMMAND_SEARCH,
        'sphinx'
    ]

    if index is not None:
        paths.insert(0, 'sphinx/%s' % index)

    return select_template(['%s/%s' % (path, name) for path in paths])


def _is_sourcable_field(field):
    # We can use float fields in 0.98
    if sphinxapi.VER_COMMAND_SEARCH >= 0x113 and (isinstance(field, models.FloatField) or isinstance(field, models.DecimalField)):
        return True
    elif isinstance(field, models.ForeignKey):
        return True
    elif isinstance(field, models.IntegerField) and field.choices:
        return True
    elif not field.rel:
        return True
    return False

# No trailing slashes on paths

if DJANGO_MINOR_VERSION < 1.2:
    DEFAULT_SPHINX_PARAMS = {
        'database_engine': _get_database_engine(),
        'database_host': settings.DATABASE_HOST,
        'database_port': settings.DATABASE_PORT,
        'database_name': settings.DATABASE_NAME,
        'database_user': settings.DATABASE_USER,
        'database_password': settings.DATABASE_PASSWORD,
    }
else:
    DEFAULT_SPHINX_PARAMS = {
        'database_engine': _get_database_engine(),
        'database_host': settings.DATABASES['default']['HOST'],
        'database_port': settings.DATABASES['default']['PORT'],
        'database_name': settings.DATABASES['default']['NAME'],
        'database_user': settings.DATABASES['default']['USER'],
        'database_password': settings.DATABASES['default']['PASSWORD'],
    }
DEFAULT_SPHINX_PARAMS.update({
    'log_path': getattr(settings, 'SPHINX_LOG_PATH', '/var/log/sphinx/searchd.log'),
    'data_path': getattr(settings, 'SPHINX_DATA_PATH', '/var/data'),
    'pid_file': getattr(settings, 'SPHINX_PID_FILE', '/var/log/searchd.pid'),
    'sphinx_host': getattr(settings, 'SPHINX_HOST', '127.0.0.1'),
    'sphinx_port': getattr(settings, 'SPHINX_PORT', '3312'),
    'sphinx_api_version': getattr(sphinxapi, 'VER_COMMAND_SEARCH', 0x113),
})


def get_index_context(index):
    params = DEFAULT_SPHINX_PARAMS
    params.update({
        'index_name': index,
        'source_name': index,
    })

    return params


def get_conf_context():
    params = DEFAULT_SPHINX_PARAMS
    return params


def process_options_for_model(options=None):
    pass


def _get_sphinx_attr_type_for_field(field):
    string_fields = [CharField, EmailField, FilePathField, IPAddressField, SlugField, TextField, URLField]
    int_fields = [AutoField, IntegerField, PositiveIntegerField, PositiveSmallIntegerField, SmallIntegerField]
    big_int_fields = [BigIntegerField]
    float_fields = [DecimalField, FloatField]
    timestamp_fields = [DateField, DateTimeField, TimeField]
    bool_fields = [BooleanField, NullBooleanField]
    ft = type(field)

    if ft in string_fields:
        return 'string'
    elif ft in int_fields:
        return 'uint'
    elif ft in big_int_fields:
        return 'bigint'
    elif ft in float_fields:
        return 'float'
    elif ft in timestamp_fields:
        return 'timestamp'
    elif ft in bool_fields:
        return 'bool'


# Generate for single models
def generate_config_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_model(model_class, index, sphinx_params) + "\n\n" + \
    generate_index_for_model(model_class, index, sphinx_params)


def generate_index_for_model(model_class, index=None, sphinx_params={}):
    """\
    Generates an index configuration for a model. Respects template
    overrides from the user for individual models. Any files in settings
    that are specified in the format `sphinx/Mymodel.index`
    will be loaded instead of the default source.conf and index.conf boilerplate
    provided with django-sphinx. Remember, models must be registered with a
    SphinxSearch() manager to be recognized by django-sphinx.\
    """
    try:
        t = _get_template('%s_index.conf' % model_class.__name__, index)
    except:
        t = _get_template('index.conf', index)

    if index is None:
        index = model_class._meta.db_table

    params = get_index_context(index)
    params.update(sphinx_params)

    c = Context(params)

    return t.render(c)


def generate_content_type_for_model(model_class):
    pass


def _process_options_for_model_fields(options, model_fields, model_class):
    fields = []
    indexes = []
    stored_attrs = {}

    # get model pk fields (supports compositepks)
    pks = [pk for pk in getattr(model_class._meta, 'pks', [model_class._meta.pk])]

    # добавляем в список явно указанные поля
    # исключая related-поля. Для них есть отдельный список
    included_fields = options.get('included_fields', [])
    for field in pks:
        # собираем в список все поля кроме private_key
        if field.column not in included_fields and type(field) != AutoField:
            included_fields.insert(0, field.column)
        if type(field) == AutoField or _get_sphinx_attr_type_for_field(field) in ['uint', 'bigint']:
            indexes.append(field)
        else:
            raise TypeError(u'В данный момент не поддерживаются первичные ключи, нечислового типа')

    [fields.append(f) for f in model_fields if not hasattr(f.rel, 'to') and f.name in included_fields]

    # удаляем исключенные поля
    excluded_fields = options.get('excluded_fields', [])
    for field in pks:
        if field.column in excluded_fields:
            excluded_fields.pop(excluded_fields.index(field.column))
    [fields.pop(fields.index(f)) for f in model_fields if f.name in excluded_fields]


    # наполняем список stored полей, так же исключая related-поля,
    # и первичный ключ, если он числовой (автоинкремент)
    stored_attrs_list = options.get('stored_attributes', [])
    for column in stored_attrs_list:
        field = model_class._meta.get_field(column)
        if field and not hasattr(field.rel, 'to') and not type(field) == AutoField:
            attr_type = _get_sphinx_attr_type_for_field(field)
            stored_attrs.setdefault(attr_type, []).append(field.column)

    return (fields, indexes, stored_attrs)


def _process_related_fields_for_model(options, model_class):
    related_field_names = options.get('related_fields', [])

    # De-normalize specified related fields into the index for this source
    app_label = model_class._meta.app_label
    local_table = model_class._meta.db_table
    join_statements = []
    related_fields = []
    join_tables = []
    content_types = []

    for related in related_field_names:
        local_field_name, related_model_field_name = related.split('__')

        local_field = model_class._meta.get_field(local_field_name)

        local_field_column = local_field.column

        related_model = local_field.rel.to
        related_table = related_model._meta.db_table
        related_column = local_field.rel.get_related_field().column
        #TODO: проверять существование полей и моделей!!!

        if related_table not in join_tables:
            join_tables.append(related_table)
            join_statements.append(
                'INNER JOIN %s ON %s.%s=%s.%s ' % (related_table, local_table, local_field_column, related_table, related_column)
            )
            # Add content type for related field model
            content_type = ContentType.objects.get(app_label=related_model._meta.app_label, model=related_model._meta.object_name.lower()).pk
            related_fields.append('%s as %s_content_type' % (content_type, related_table))
            content_types.append('%s_content_type' % related_table)

        related_fields.append('%s.%s as %s__%s' % (related_table, related_column, local_field_name, related_model_field_name))

    return (related_fields, join_statements, content_types)


def _process_related_attributes_for_model(options, model_class):
    related_attributes_list = options.get('related_stored_attributes', [])

    related_attributes = {}

    for attribute in related_attributes_list:
        local_field_name, related_model_field_name = attribute.split('__')

        local_field = model_class._meta.get_field(local_field_name)

        related_model = local_field.rel.to
        related_field = related_model._meta.get_field(related_model_field_name)

        related_field_type = _get_sphinx_attr_type_for_field(related_field)

        related_attributes.setdefault(related_field_type, []).append(attribute)

    return related_attributes

def get_source_context(tables, index_name, fields, indexes,
                        related_fields, join_statements, content_types,
                        stored_attrs, stored_related_attrs,
                        document_content_type):

    # remove the doc id
    if len(indexes) > 1:
        raise NotImplementedError (u'Поддержка генерации ID документа из составного индекса пока отсутствует')
    else:
        doc_id = indexes[0]

    context = DEFAULT_SPHINX_PARAMS
    context.update({
        'tables': tables,
        'source_name': index_name,
        'index_name': index_name,
        'database_engine': _get_database_engine(),

        'fields': ['%s.%s' % (f.model._meta.db_table, f.column) for f in fields],
        'related_fields': related_fields,
        'join_statements': join_statements,
        'content_types': content_types,

        'stored_attrs': stored_attrs,
        'stored_related_attrs': stored_related_attrs,

        'document_id': '%s<<%i|%s.%s' % (document_content_type.id,
                                               DOCUMENT_ID_SHIFT,
                                               doc_id.model._meta.db_table,
                                               doc_id.column)
    })

    try:
        #TODO: разобраться в этой магии
        from django.contrib.gis.db.models import PointField
        context.update({
            'gis_columns': [f.column for f in fields if isinstance(f, PointField)],
            'srid': getattr(settings, 'GIS_SRID', 4326),  # reasonable lat/lng default
        })
        if context['database_engine'] == 'pgsql' and context['gis_columns']:
            context['fields'].extend(["radians(ST_X(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_longitude, radians(ST_Y(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_latitude" % {'field_name': f, 'srid': context['srid']} for f in context['gis_columns']])
    except ImportError:
        # GIS not supported
        pass

    return context


def generate_source_for_model(model_class, index=None, sphinx_params={}):
    """\
    Generates a source configuration for a model. Respects template
    overrides from the user for individual models. Any files in settings
    that are specified in the format `sphinx/Mymodel.source` will be loaded
    instead of the default source.conf boilerplate provided with django-sphinx.
    Remember, models must be registered with a SphinxSearch() manager to be
    recognized by django-sphinx.\
    """
    try:
        t = _get_template('%s_source.conf' % model_class.__name__, index)
    except:
        t = _get_template('source.conf', index)

    def _the_tuple(f):
        return (
            f.__class__,
            f.column,
            getattr(f.rel, 'to', None),
            f.choices,
            f.model._meta.db_table,  # Verbose table name
            '%s_%s' % (f.model._meta.db_table, f.column)  # Alias
        )

    model_fields = model_class._meta.fields
    options = model_class.__sphinx_options__

    fields, indexes, stored_attrs = _process_options_for_model_fields(options, model_fields, model_class)

    related_fields, join_statements, content_types = _process_related_fields_for_model(options, model_class)
    related_stored_attrs = _process_related_attributes_for_model(options, model_class)

    table = model_class._meta.db_table
    if index is None:
        index = table

    context = get_source_context(
        ['table'],
        index,
        fields,
        indexes,
        related_fields,
        join_statements,
        content_types,
        stored_attrs,
        related_stored_attrs,
        ContentType.objects.get_for_model(model_class),
    )

    context.update({
        'table_name': table,
        'primary_key': model_class._meta.pk.column,
    })
    context.update(sphinx_params)

    c = Context(context)

    return t.render(c)

# Generate for multiple models (search UNIONs)
# Похоже, это пока не работает

def generate_config_for_models(model_classes, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_models(model_classes, index, sphinx_params) + "\n\n" + generate_index_for_models(model_classes, index, sphinx_params)


def generate_index_for_models(model_classes, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('index-multiple.conf', index)

    if index is None:
        index = '_'.join(m._meta.db_table for m in model_classes)

    params = get_index_context(index)
    params.update(sphinx_params)

    c = Context(params)

    return t.render(c)


def generate_source_for_models(model_classes, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('source-multiple.conf', index)

    # We need to loop through each model and find only the fields that exist *exactly* the
    # same across models.
    def _the_tuple(f):
        return (f.__class__, f.column, getattr(f.rel, 'to', None), f.choices)

    valid_fields = [_the_tuple(f) for f in model_classes[0]._meta.fields if _is_sourcable_field(f)]
    for model_class in model_classes[1:]:
        valid_fields = [_the_tuple(f) for f in model_class._meta.fields if _the_tuple(f) in valid_fields]

    tables = []
    for model_class in model_classes:
        tables.append((model_class._meta.db_table, ContentType.objects.get_for_model(model_class)))

    if index is None:
        index = '_'.join(m._meta.db_table for m in model_classes)

    params = get_source_context(tables, index, valid_fields)
    params.update(sphinx_params)

    c = Context(params)

    return t.render(c)


def generate_sphinx_config(sphinx_params={}):
    t = _get_template('sphinx.conf')

    params = get_conf_context()
    params.update(sphinx_params)
    c = Context(params)
    return t.render(c)
