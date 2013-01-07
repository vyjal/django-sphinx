# coding: utf-8

import django


from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields import *
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.template import Context
from django.template.loader import select_template

from djangosphinx.conf import *

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
    raise ValueError("Only MySQL and PostgreSQL engines are supported by Sphinx.")


def _get_template(name, index=None):

    paths = [
        'sphinx/'
    ]

    if index is not None:
        paths.insert(0, 'sphinx/%s_' % index)

    return select_template(['%s%s' % (path, name) for path in paths])

def _is_sourcable_field(field):
    # We can use float fields in 0.98
    if isinstance(field, models.FloatField) or isinstance(field, models.DecimalField):
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
DEFAULT_SPHINX_PARAMS.update(SEARCHD_SETTINGS)


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


def get_sphinx_attr_type_for_field(field):
    types = dict(
        string=(CharField, EmailField, FilePathField, IPAddressField, SlugField, TextField, URLField),
        uint=(AutoField, IntegerField, PositiveIntegerField,
              PositiveSmallIntegerField, SmallIntegerField,
              ForeignKey, OneToOneField),

        bigint=(BigIntegerField),
        float=(DecimalField, FloatField),
        timestamp=(DateField, DateTimeField, TimeField),
        bool=(BooleanField, NullBooleanField),

        #multi=(ManyToManyField,)
    )

    for t in types:
        if isinstance(field, types[t]):
            return t

    warnings.warn('Unknown field type: `%s`' % type(field))
    return 'unknown'


# Generate for single models
def generate_config_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_model(model_class, index, sphinx_params)\
    #       + "\n\n" + \
    #generate_index_for_model(model_class, index, sphinx_params)


def generate_index_for_model(model_class, index=None, sphinx_params={}):
    """\
    Generates an index configuration for a model. Respects template
    overrides from the user for individual models. Any files in settings
    that are specified in the format `sphinx/Mymodel.index`
    will be loaded instead of the default source.conf and index.conf boilerplate
    provided with django-sphinx. Remember, models must be registered with a
    SphinxSearch() manager to be recognized by django-sphinx.\
    """
    options = model_class.__sphinx_options__

    build_realtime = options.get('realtime', False)
    build_delta = options.get('delta', False)

    t = _get_template('index.conf', index)

    if index is None:
        index = model_class._meta.db_table

    params = get_index_context(index)
    params.update(sphinx_params)

    c = Context(params)

    d = t.render(c)

def _process_options_for_model_fields(options, model_fields, model_class):
    fields = []
    indexes = []
    stored_attrs = {}

    # get model pk fields (supports compositepks)
    pks = [pk for pk in getattr(model_class._meta, 'pks', [model_class._meta.pk])]

    # добавляем в список явно указанные поля
    # исключая related-поля. Для них есть отдельный список
    included_fields = options.get('included_fields', [])
    excluded_fields = options.get('excluded_fields', [])

    if 'stored_string_attributes' in options:
        warnings.warn('`stored_string_attributes` is deprecated. Use `stored_attributes` instead.', DeprecationWarning)
        stored_attrs_list = list(options['stored_string_attributes'])
    else:
        stored_attrs_list = options.get('stored_attributes', [])

    stored_fields_list = options.get('stored_fields', [])

    stored_fields = [f for f in stored_fields_list if
                                                        get_sphinx_attr_type_for_field(
                                                            model_class._meta.get_field(f)
                                                        ) == 'string']

    stored_attrs_list = [f for f in stored_attrs_list if f not in stored_fields]

    for field in pks:
        # собираем в список все поля кроме private_key
        if field.column not in included_fields and type(field) != AutoField:
            included_fields.insert(0, field.column)
        # убираем из исключенных все private keys
        if field.column in excluded_fields:
            excluded_fields.pop(excluded_fields.index(field.column))
        # убираем private keys из списка stored атрибутов
        if field.column in stored_attrs_list:
            stored_attrs_list.pop(stored_attrs_list.index(field.column))

        # собираем массив числовых private_keys
        if type(field) == AutoField or get_sphinx_attr_type_for_field(field) in ['uint', 'bigint']:
            indexes.append(field)
        else:
            raise TypeError('Currently, non-numeric primary key type is not supported')

    # удаляем из списка stored все related поля. а так же autoincrement
    for column in stored_attrs_list[:]:
        field = model_class._meta.get_field(column)
        if hasattr(field.rel, 'to') or type(field) == AutoField:
            stored_attrs_list.pop(stored_attrs_list.index(column))

    # добавляем stored поля в список выбранных, если они там отсутствуют
    [included_fields.append(f) for f in stored_attrs_list if f not in included_fields]
    [included_fields.append(f) for f in stored_fields if f not in included_fields]

    [fields.append(f) for f in model_fields if not hasattr(f.rel, 'to') and f.name in included_fields]

    # удаляем исключенные поля
    [fields.pop(fields.index(f)) for f in model_fields if f.name in excluded_fields and f in fields]
    [stored_attrs_list.pop(fields.index(f)) for f in excluded_fields if f in stored_attrs_list]
    [stored_fields_list.pop(fields.index(f)) for f in excluded_fields if f in stored_fields_list]

    # если included_fields не заполнен - выбираем все поля модели
    if not fields:
        fields = [f for f in model_class._meta.fields if f not in pks and f not in excluded_fields]
        indexes = pks

    # наполняем список stored полей

    # добавляем в stored все нестроковые поля, не являющиеся private keys
    for field in fields:
        if field not in pks and get_sphinx_attr_type_for_field(field) != 'string':
            attr_type = get_sphinx_attr_type_for_field(field)
            stored_attrs.setdefault(attr_type, []).append(field.column)

    # добавляем в stored заданные вручную строковые поля
    for column in stored_attrs_list:
        field = model_class._meta.get_field(column)
        if get_sphinx_attr_type_for_field(field) == 'string':

            attr_type = get_sphinx_attr_type_for_field(field)
            stored_attrs.setdefault(attr_type, []).append(field.column)

    return (fields, indexes, stored_attrs, stored_fields)

def _process_mva_fields_for_model(options, model_class, content_type, indexes):

    if len(indexes) > 1:
        raise NotImplementedError ('Support for generating document identifier of a composite index is not yet available')
    else:
        doc_id = indexes[0]

    mvas = dict()

    model_table = model_class._meta.db_table
    model_pk = doc_id.column

    mva_fields = options.get('mva_fields', [])

    for field in model_class._meta.many_to_many:
        if field.name in mva_fields:

            # а теперь магия :)
            m2m_model_class = getattr(model_class, field.name).through
            m2m_table = m2m_model_class._meta.db_table
            related_model_class = field.rel.to
            model_target_column = model_class._meta.get_field(field.m2m_target_field_name()).column
            m2m_model_column = field.m2m_column_name()
            m2m_related_column = m2m_model_class._meta.get_field(field.m2m_reverse_field_name()).column

            related_target_field = related_model_class._meta.get_field(field.m2m_reverse_target_field_name())

            doc_id = content_type.pk if _get_database_engine() == 'mysql' else 'CAST(%i as BIGINT)' % content_type.pk

            query = ''.join(['SELECT %s<<%i|%s.%s, %s.%s ' % (doc_id,
                                                              DOCUMENT_ID_SHIFT,

                                                              model_table,
                                                              model_pk,

                                                              m2m_table,
                                                              m2m_related_column,
                                                              ),

                            'FROM %s ' % (model_table),
                            'INNER JOIN %s ON %s.%s=%s.%s ' % (m2m_table,

                                                               m2m_table,
                                                               m2m_model_column,
                                                               model_table,
                                                               model_target_column,
                                                               ),
                            ])

            mvas[field.name] = {
                'type': get_sphinx_attr_type_for_field(related_target_field),
                'tag': field.name,
                'source_type': 'query',
                'query': query,
                }

    return mvas

def _process_related_fields(fields, options, model_class):
    related_field_names = options.get('related_fields', [])

    local_table = model_class._meta.db_table
    related_fields = []
    related_stored_attrs = {}
    join_tables = []
    join_statements = []

    for related in related_field_names:
        parts = related.split('__')
        if len(parts) == 1:
            field = model_class._meta.get_field(related)

            if not isinstance(field, (ForeignKey, OneToOneField)):
                raise TypeError('Related_fields list can only contain fields '
                                'of ForeignKey and OneToOneField types')

            related_fields.append('%s.%s as %s' % (local_table, field.column, field.name))

            related_stored_attrs.setdefault('uint', []).append(field.name)
        elif len(parts) == 2:
            local_field_name, related_model_field_name = parts

            local_field = model_class._meta.get_field(local_field_name)

            local_field_column = local_field.column

            related_model = local_field.rel.to
            related_table = related_model._meta.db_table
            related_pk_field = local_field.rel.get_related_field()
            related_pk_column = related_pk_field.column

            related_field = related_model._meta.get_field(related_model_field_name)

            if not isinstance(related_field, OneToOneField):
                raise TypeError('Only OneToOne relations can be added to the index '
                                'for `%s.%s`. Not `%s`.' % (model_class._meta.app_label,
                                                            model_class._meta.module_name,
                                                            local_field_name))

            related_field_type = get_sphinx_attr_type_for_field(related_field)

            related_column = related_field.column
            #TODO: проверять существование полей и моделей!!!

            if related_table not in join_tables:
                join_tables.append(related_table)
                join_statements.append(
                    'INNER JOIN %s ON %s.%s=%s.%s ' % (related_table,
                                                       local_table,
                                                       local_field_column,
                                                       related_table,
                                                       related_pk_column)
                )

            related_fields.append('%s.%s as %s__%s' % (related_table,
                                                       related_column,
                                                       local_field_name,
                                                       related_model_field_name))
            if related_field_type != 'string':
                related_stored_attrs.setdefault(related_field_type, []).append('%s__%s' % (local_field_name,
                                                                                           related_model_field_name))
        else:
            raise NotImplementedError('Oops... we need to go deeper?')


    return (related_fields, related_stored_attrs, join_statements)


def get_source_context(tables, index_name, fields, indexes, mva_fields,
                        related_fields, join_statements, content_types,
                        stored_attrs, stored_string_fields, stored_related_attrs,
                        document_content_type):

    if len(indexes) > 1:
        raise NotImplementedError ('Support for generating document identifier of a composite index is not yet available')
    else:
        doc_id = indexes[0]

    content_type_id = document_content_type.pk if _get_database_engine() == 'mysql' \
                                                else 'CAST(%i as BIGINT)' % document_content_type.pk

    context = DEFAULT_SPHINX_PARAMS
    context.update({
        'tables': tables,
        'source_name': index_name,
        'index_name': index_name,
        'database_engine': _get_database_engine(),

        'fields': ['%s.%s' % (f.model._meta.db_table, f.column) for f in fields],
        'mva_fields': mva_fields,
        'related_fields': related_fields,
        'join_statements': join_statements,
        'content_types': content_types,

        'stored_attrs': stored_attrs,
        'stored_string_fields': stored_string_fields,
        'stored_related_attrs': stored_related_attrs,

        'document_id': '%s<<%i|%s.%s' % (content_type_id,
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
    results = list()
    options = model_class.__sphinx_options__

    build_realtime = options.get('realtime', False)
    build_delta = options.get('delta', False)

    if build_realtime and build_delta:
        raise ImproperlyConfigured('You\'ll have to determine what you want...')

    main_source_template = _get_template('source.conf', index)
    main_index_template = _get_template('index.conf', index)

    content_type = ContentType.objects.get_for_model(model_class)
    model_fields = model_class._meta.fields

    fields, indexes, stored_attrs, stored_fields = _process_options_for_model_fields(options, model_fields, model_class)

    mva_fields = _process_mva_fields_for_model(options, model_class, content_type, indexes)

    content_types = []

    related_fields, related_stored_attrs, join_statements = _process_related_fields(fields, options, model_class)

    table = model_class._meta.db_table
    if index is None:
        index = table

    # Основной источник данных
    main_source_context = get_source_context(
        ['table'],
        index,
        fields,
        indexes,
        mva_fields,
        related_fields,
        join_statements,
        content_types,
        stored_attrs,
        stored_fields,
        related_stored_attrs,
        content_type,
    )

    main_source_context.update({
        'table_name': table,
        'primary_key': model_class._meta.pk.column,
    })
    main_source_context.update(sphinx_params)

    msc = Context(main_source_context)
    main_source_config = main_source_template.render(msc)
    results.append(main_source_config)

    # Основной индекс
    main_index_context = get_index_context(index)
    main_index_context.update(sphinx_params)

    mic = Context(main_index_context)
    main_index_config = main_index_template.render(mic)
    results.append(main_index_config)

    # RealTime-индекс

    if build_realtime:
        rt_fields = list()
        rt_stored_strings = stored_attrs.get('string', [])
        for field in fields:
            if get_sphinx_attr_type_for_field(field) == 'string' and field.name not in rt_stored_strings:
                rt_fields.append(field)

        rt_mva = dict()
        for k, v in mva_fields.iteritems():
            if v['type'] == 'uint':
                rt_mva[k] = 'multi'
            elif v['type'] == 'bigint':
                rt_mva[k] = 'multi_64'
            else:
                raise TypeError('Only `int` and `bigint` types allowed for MVA in RT')

        bool_list = stored_attrs.pop('bool', [])
        bool_list.extend(related_stored_attrs.pop('bool', []))

        for field in bool_list:
            stored_attrs.setdefault('uint', []).append(field)

        for t, f_list in related_stored_attrs.iteritems():
            stored_attrs.setdefault(t, []).extend(f_list)

        rt_index = '%s_rt' % index
        rt_index_context = DEFAULT_SPHINX_PARAMS
        rt_index_context.update(dict(
            index_name=rt_index,
            rt_fields=rt_fields,
            rt_attrs=stored_attrs,
            rt_string_attrs=stored_fields,
            rt_mva=rt_mva,
        ))

        rt_index_template = _get_template('realtime/index.conf', index)
        rtic = Context(rt_index_context)
        rt_index_config = rt_index_template.render(rtic)
        results.append(rt_index_config)

    if build_delta:
        pass

    return '\n\n'.join(results)

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
