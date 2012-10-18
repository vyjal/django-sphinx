import django
from django.conf import settings
from django.template import Template, Context

from django.db import models
from django.contrib.contenttypes.models import ContentType

import os.path

import djangosphinx.apis.current as sphinxapi
from django.template.loader import select_template

__all__ = ('generate_config_for_model', 'generate_config_for_models', 'generate_sphinx_config')

DJANGO_MINOR_VERSION = float(".".join([str(django.VERSION[0]), str(django.VERSION[1])]))

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
    raise ValueError, "Only MySQL and PostgreSQL engines are supported by Sphinx."

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
    'sphinx_api_version': getattr(settings, 'SPHINX_API_VERSION', 0x113),
})

def get_index_context(index):
    params = DEFAULT_SPHINX_PARAMS
    params.update({
        'index_name': index,
        'source_name': index,
    })

    return params

def get_source_context(tables, index, valid_fields, content_type=None):
    params = DEFAULT_SPHINX_PARAMS
    params.update({
        'tables': tables,
        'source_name': index,
        'index_name': index,
        'database_engine': _get_database_engine(),
        'field_names': [f[1] for f in valid_fields],
        'group_columns': [f[1] for f in valid_fields if f[2] or isinstance(f[0], models.BooleanField) or isinstance(f[0], models.IntegerField)],
        'date_columns': [f[1] for f in valid_fields if issubclass(f[0], models.DateTimeField) or issubclass(f[0], models.DateField)],
        'float_columns': [f[1] for f in valid_fields if isinstance(f[0], models.FloatField) or isinstance(f[0], models.DecimalField)],
    })
    if content_type is not None:
        params['field_names'].append("%s as content_type" % content_type.id)
    try:
        from django.contrib.gis.db.models import PointField
        params.update({
            'gis_columns': [f.column for f in valid_fields if isinstance(f, PointField)],
            'srid': getattr(settings, 'GIS_SRID', 4326), # reasonable lat/lng default
        })
        if params['database_engine'] == 'pgsql' and params['gis_columns']:
            params['field_names'].extend(["radians(ST_X(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_longitude, radians(ST_Y(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_latitude" % {'field_name': f, 'srid': params['srid']} for f in params['gis_columns']])
    except ImportError:
        # GIS not supported
        pass
    return params

def get_conf_context():
    params = DEFAULT_SPHINX_PARAMS
    return params

def process_options_for_model(options=None):
    pass

# Generate for single models

def generate_config_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_model(model_class, index, sphinx_params) + "\n\n" + \
    generate_index_for_model(model_class, index, sphinx_params)

def generate_index_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates an index configuration for a model. Respects template
    overrides from the user for individual models. Any files in settings
    that are specified in the format `sphinx/Mymodel.index` 
    will be loaded instead of the default source.conf and index.conf boilerplate 
    provided with django-sphinx. Remember, models must be registered with a 
    SphinxSearch() manager to be recognized by django-sphinx.
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

def generate_source_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates a source configuration for a model. Respects template
    overrides from the user for individual models. Any files in settings
    that are specified in the format `sphinx/Mymodel.source` will be loaded 
    instead of the default source.conf boilerplate provided with django-sphinx. 
    Remember, models must be registered with a SphinxSearch() manager to be 
    recognized by django-sphinx.
    """
    try:
        t = _get_template('%s_source.conf' % model_class.__name__, index)
    except:
        t = _get_template('source.conf', index)

    def _the_tuple(f):
        return (f.__class__, f.column, getattr(f.rel, 'to', None), f.choices)
    
    model_fields = model_class._meta.fields
    modified_fields = []

    options = model_class.__sphinx_options__
    
    # Remove optionally excluded fields from indexing
    try:
        excluded_fields = options['excluded_fields']
        [modified_fields.append(f) for f in model_fields if f.name not in excluded_fields]
    except:
        pass
    # Remove fields not specified as included
    try:
        included_fields = options['included_fields']
        if 'id' not in included_fields:
            included_fields.append('id')
        [modified_fields.append(f) for f in model_fields if f.name in included_fields]
    except:
        pass

    if len(modified_fields) > 0:
        valid_fields = [_the_tuple(f) for f in modified_fields if _is_sourcable_field(f)]
    else:
        valid_fields = [_the_tuple(f) for f in model_fields if _is_sourcable_field(f)]
    
    table = model_class._meta.db_table
    
    if index is None:
        index = table
        
    params = get_source_context([table], index, valid_fields, ContentType.objects.get_for_model(model_class))
    params.update({
        'table_name': table,
        'primary_key': model_class._meta.pk.column,
    })
    params.update(sphinx_params)

    c = Context(params)
    
    return t.render(c)
    
# Generate for multiple models (search UNIONs)

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
