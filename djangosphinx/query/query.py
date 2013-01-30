# coding: utf-8
from __future__ import unicode_literals

__author__ = 'ego'

import MySQLdb
import re
import warnings

from threading import local

from django.core.signals import request_finished
from django.utils.encoding import force_unicode

from djangosphinx.conf import SEARCHD_SETTINGS

class ConnectionError(Exception):
   pass


class ConnectionHandler(object):
    def __init__(self):
        self._connections = local()

    def _connection(self):
        if hasattr(self._connections, 'sphinx_database_connection'):
            return getattr(self._connections, 'sphinx_database_connection')

        conn = MySQLdb.connect(host=SEARCHD_SETTINGS['sphinx_host'], port=SEARCHD_SETTINGS['sphinx_port'])
        setattr(self._connections, 'sphinx_database_connection', conn)
        return conn

    connection = property(_connection)

    def cursor(self):
        return self.connection.cursor()

    def close(self): # закрывает подключение к Sphinx
        if hasattr(self._connections, 'sphinx_database_connection'):
            conn = getattr(self._connections, 'sphinx_database_connection')

            conn.close()

            delattr(self._connections, 'sphinx_database_connection')


conn_handler = ConnectionHandler()


def close_sphinx_connection(**kwargs):
    conn_handler.close()

request_finished.connect(close_sphinx_connection)


class SphinxQuery(object):
    _arr_regexp = re.compile(r'^([a-z]+)\[(\d+)\]', re.I)

    def __init__(self, query=None, args=None):

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

        self.cursor = conn_handler.cursor()
        self.cursor.execute(self._query, self._query_args)

    def _get_meta(self):
        if not self._result:
            self._get_results()

        _meta = dict()
        c = conn_handler.cursor()
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
