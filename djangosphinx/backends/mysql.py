#coding: utf-8

__author__ = 'ego'

import MySQLdb
import re
import warnings
from collections import OrderedDict
from threading import local

from django.utils.encoding import force_unicode

from djangosphinx.conf import *
from djangosphinx.backends.base import BaseSphinxQuerySet
from djangosphinx.constants import QUERY_RANKERS, QUERY_OPTIONS, FILTER_CMP_OPERATIONS, FILTER_CMP_INVERSE
from django.core.signals import request_finished

__all__ = ['SphinxQuerySet']

class ConnectionHandler(object):
    def __init__(self):
        self._connections = local()

    def _connection(self):
        if hasattr(self._connections, 'sphinx_database_connection'):
            return getattr(self._connections, 'sphinx_database_connection')

        conn = MySQLdb.connect(host=SEARCHD_SETTINGS['sphinx_host'], port=SEARCHD_SETTINGS['sphinx_mysql_port'])
        setattr(self._connections, 'sphinx_database_connection', conn)
        return conn

    connection = property(_connection)

conn_handler = ConnectionHandler()

# закрываем
def close_connection(**kwargs):
    conn_handler.connection.close()

request_finished.connect(close_connection)

class SphinxQuery(object):
    _arr_regexp = re.compile(r'^([a-z]+)\[(\d+)\]', re.I)

    def __init__(self, query=None, args=None):
        self._db = conn_handler.connection

        self._query = query
        self._query_args = args
        self._result = None
        self._meta = None

        self._result_cache = []

        self.cursor = None

    def __iter__(self):
        return iter(self.next())

    def next(self):
        if self.cursor is None:
            self._get_results()

        row = self.cursor.fetchone()

        if not row:
            raise StopIteration

        return row

    def query(self, query, args=None):
        return self._clone(_query=force_unicode(query), _query_args=args)

    def count(self, ):
        if self._meta is None:
            self._get_meta()

        return self._meta['total_found']

    def metadata(self):
        if self._meta is None:
            self._get_meta()

        return self._meta.copy()

    meta = property(metadata)

    def _clone(self, **kwargs):
        q = self.__class__()
        q.__dict__.update(self.__dict__.copy())

        q._result = None
        q._meta = None
        q._query = None

        for k, v in kwargs.iteritems():
            setattr(q, k, v)

        return q


    def _get_results(self):
        if self._query is None:
            raise Exception

        self.cursor = self._db.cursor()
        self.cursor.execute(self._query, self._query_args)

    def _get_meta(self):
        if not self._result:
            self._get_results()

        _meta = dict()
        c = self._db.cursor()
        c.execute('SHOW META')

        while True:
            row = c.fetchone()

            if not row:
                break

            key = row[0]
            val = row[1]
            m = re.match(self._arr_regexp, key)
            if m:
                key, v = m.groups()
                _meta.setdefault(key, {})[v] = val
            else:
                _meta[key] = val

        if 'keyword' in _meta:
            _meta['words'] = {}
            for k, v in _meta['keyword'].iteritems():
                _meta['words'][v] = {
                    'hits': _meta['hits'][k],
                    'docs': _meta['docs'][k],
                }
            _meta.pop('keyword')
            _meta.pop('hits')
            _meta.pop('docs')

        _meta['fields'] = {}
        for k, v in enumerate(self.cursor.description):
            _meta['fields'][v[0]] = int(k)

        self._meta = _meta


class SphinxQuerySet(BaseSphinxQuerySet):

    def __init__(self, model=None, using=None, **kwargs):
        super(SphinxQuerySet, self).__init__(model, using, **kwargs)

        self._db = conn_handler.connection

    def _get_data(self):
        assert(self._indexes)

        self._iter = SphinxQuery(self.query_string, self._query_args)
        self._result_cache = []
        self._metadata = self._iter.meta
        self._fill_cache()

    def filter(self, **kwargs):
        filters = self._filters.copy()
        return self._clone(_filters=self._process_filters(filters, False, **kwargs))

    def exclude(self, **kwargs):
        filters = self._excludes.copy()
        return self._clone(_excludes=self._process_filters(filters, True, **kwargs))

    def values(self, *args, **kwargs):
        fields = ''
        aliases = {}
        if args:
            fields = '`%s`' % '`, `'.join(args)
        if kwargs:
            for k, v in kwargs.iteritems():
                aliases[k] = '%s AS `%s`' % (v, k)

        if fields or aliases:
            return self._clone(_fields=fields, _aliases=aliases)
        return self

    # Currently only supports grouping by a single column.
    # The column however can be a computed expression
    def group_by(self, field):
        return self._clone(_group_by='GROUP BY `%s`' % field)

    def order_by(self, *args):
        sort_by = []
        for arg in args:
            order = 'ASC'
            if arg[0] == '-':
                order = 'DESC'
                arg = arg[1:]
            if arg == 'pk':
                arg = 'id'

            sort_by.append('`%s` %s' % (arg, order))

        if sort_by:
            return self._clone(_order_by='ORDER BY %s' % ', '.join(sort_by))
        return self

    def group_order(self, *args):
        sort_by = []
        for arg in args:
            order = 'ASC'
            if arg[0] == '-':
                order = 'DESC'
                arg = arg[1:]
            if arg == 'pk':
                arg = 'id'

            sort_by.append('`%s` %s' % (arg, order))

        if sort_by:
            return self._clone(_group_order_by='WITHIN GROUP ORDER BY %s' % ', '.join(sort_by))
        return self



    def _format_options(self, **kwargs):
        opts = []
        for k, v in kwargs.iteritems():
            if k in QUERY_OPTIONS:
                assert(isinstance(v, QUERY_OPTIONS[k]))

                if k == 'ranker':
                    assert(v in QUERY_RANKERS)
                elif k == 'reverse_scan':
                    v = int(v) & 0x0000000001
                elif k in ('field_weights', 'index_weights'):
                    v = '(%s)' % ', '.join(['%s=%s' % (x, v[x]) for x in v])
                #elif k == 'comment':
                #    v = '\'%s\'' % self.escape(v)

                opts.append('%s=%s' % (k, v))

        if opts:
            return dict(_query_opts='OPTION %s' % ','.join(opts))
        return None



    def _fill_cache(self, num=None):
        fields = self.meta['fields'].copy()
        id_pos = fields.pop('id')
        ct = None
        results = {}

        docs = OrderedDict()

        if self._iter:
            try:
                while True:
                    doc = self._iter.next()
                    doc_id = doc[id_pos]

                    obj_id, ct = self._decode_document_id(int(doc_id))

                    results.setdefault(ct, {})[obj_id] = {}

                    docs.setdefault(doc_id, {})['results'] = results[ct][obj_id]
                    docs[doc_id]['data'] = {}

                    for field in fields:
                        docs[doc_id]['data'].setdefault('fields', {})[field] = doc[fields[field]]
            except StopIteration:
                self._iter = None

                self._format_cache(docs, results, ct)

    def _qstring(self):
        if not self._query_string:
            self._build_query()
        return self._query_string

    query_string = property(_qstring)

    def _get_passages(self, instance):
        fields = self._get_doc_fields(instance)

        docs = [getattr(instance, f) for f in fields]
        opts = self.passages if self.passages else ''

        doc_format = ', '.join('%s' for x in range(0, len(fields)))
        query = 'CALL SNIPPETS (({0:>s}), \'{1:>s}\', %s {2:>s})'.format(doc_format,
                                                                        instance.__sphinx_indexes__[0],
                                                                        opts)
        docs.append(self._query)

        c = self._db.cursor()
        count = c.execute(query, docs)

        passages = {}
        for field in fields:
            passages[field] = c.fetchone()[0].decode('utf-8')

        return passages

    def _build_query(self):
        self ._query_args = []

        q = ['SELECT']
        if self._fields:
            q.append(self._fields)
            if self._aliases:
                q.append(',')

        if self._aliases:
            q.append(', '.join(self._aliases.values()))

        q.extend(['FROM', ', '.join(self._indexes)])

        if self._query or self._filters or self._excludes:
            q.append('WHERE')
        if self._query:
            q.append('MATCH(%s)')
            self._query_args.append(self._query)

            if self._filters or self._excludes:
                q.append('AND')
        if self._filters:
            q.append(' AND '.join(self._filters.values()))
            if self._excludes:
                q.append('AND')
        if self._excludes:
            q.append(' AND '.join(self._excludes.values()))

        if self._group_by:
            q.append(self._group_by)
        if self._order_by:
            q.append(self._order_by)
        if self._group_order_by:
            q.append(self._group_order_by)

        q.append('LIMIT %i, %i' % (self._offset, self._limit))

        if self._query_opts is not None:
            q.append(self._query_opts)

        self._query_string = ' '.join(q)

        return self._query_string

    def _clone(self, **kwargs):
        # Clones the queryset passing any changed args
        c = self.__class__()
        c.__dict__.update(self.__dict__.copy())

        c._result_cache = None
        c._query_string = None
        c._metadata = None
        c._iter = None

        for k, v in kwargs.iteritems():
            setattr(c, k, v)
            # почистим кеш в новом объекте, раз уж параметры запроса изменились

        return c



    def _process_filters(self, filters, exclude=False, **kwargs):
        for k, v in kwargs.iteritems():
            parts = k.split('__')
            parts_len = len(parts)
            field = parts[0]
            lookup = parts[-1]

            if parts_len == 1:  # один
                #v = self._process_single_obj_operation(parts[0], v)
                filters[k] = '`%s` %s %s' % (field,
                                             '!=' if exclude else '=',
                                             self._process_single_obj_operation(v))
            elif parts_len == 2: # один exact или список, или сравнение
                if lookup == 'in':
                    filters[k] = '`%s` %sIN (%s)' % (field,
                                                     'NOT ' if exclude else '',
                                                     ','.join(str(x) for x in self._process_obj_list_operation(v)))
                elif lookup == 'range':
                    v = self._process_obj_list_operation(v)
                    if len(v) != 2:
                        raise ValueError('Range may consist of two values')
                    if exclude:
                        # not supported by sphinx. raises error!
                        warnings.warn('Exclude range not supported by SphinxQL now!')
                        filters[k] = 'NOT `%s` BETWEEN %i AND %i' % (field, v[0], v[1])
                    else:
                        filters[k] = '`%s` BETWEEN %i AND %i' % (field, v[0], v[1])

                elif lookup in FILTER_CMP_OPERATIONS:
                    filters[k] = '`%s` %s %s' % (field,
                                                 FILTER_CMP_INVERSE[lookup]\
                                                 if exclude\
                                                 else FILTER_CMP_OPERATIONS[lookup],
                                                 self._process_single_obj_operation(v))
                else:
                    raise NotImplementedError('Related object and/or field lookup "%s" not supported' % lookup)
            else: # related
                raise NotImplementedError('Related model fields lookup not supported')

        return filters

