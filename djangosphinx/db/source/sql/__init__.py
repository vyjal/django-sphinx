#coding: utf-8

__author__ = 'ego'

class SQLIndexSource(object):

    def __init__(self, type, host, port, user, password, db, name=None):
        self.type = type
        self.sql_host = host
        self.sql_port = port
        self.sql_user = user
        self.sql_pass = password
        self.sql_db = db

        self.name = name

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name

    def contribute_to_class(self, cls, name):
        index_name = cls._meta.index_name
        source_name = '_'.join([index_name, name])

        self.set_attributes_from_name(source_name)

        cls._meta.add_source(self)

    def __repr__(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path
