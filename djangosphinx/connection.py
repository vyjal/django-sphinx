#coding: utf-8

__author__ = 'ego'
import MySQLdb
from threading import local

from djangosphinx.conf import *
from djangosphinx.backends.base import *

SPHINX_PORT = SEARCHD_SETTINGS['sphinx_mysql_port']

class ConnectionHandler(object):
    def __init__(self):
        self._connections = local()

    def _connection(self):
        if hasattr(self._connections, 'sphinx_database_connection'):
            return getattr(self._connections, 'sphinx_database_connection')

        conn = MySQLdb.connect(host=SPHINX_SERVER, port=SPHINX_PORT)
        setattr(self._connections, 'sphinx_database_connection', conn)
        return conn

    connection = property(_connection)