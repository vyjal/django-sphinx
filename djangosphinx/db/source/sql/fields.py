#coding: utf-8

from __future__ import unicode_literals

import datetime


__author__ = 'ego'

REAL_TIME_INDEX = 'rt'

class Field(object):
    name = ''
    index_type = None
    type = 'string'

    def __init__(self, name=None, alias=None, stored=False, fulltext=False):
        self.name = name
        self.alias = alias


        self.fulltext = fulltext
        if fulltext:
            if self.type != 'string':
                raise AttributeError('Non-string attributes can`t be fulltext')
            if self.index_type == REAL_TIME_INDEX:
                raise AttributeError()

            self.stored = False
        else:
            self.stored = stored

    def get_attname(self):
        return self.name

    def get_column(self):
        if self.alias:
            return self.alias
        return self.name

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)

        cls._meta.add_field(self)

    def get_internal_type(self):
        return self.__class__.__name__

    def get_query_string(self):
        if self.alias:
            return '{0} AS {1}'.format(self.name, self.alias)

        return self.name

    def get_attr_string(self):
        if not self.stored:
            return None

        if self.index_type == 'rt':
            attr_type = 'rt'
        else:
            attr_type = 'sql'
        return '{0}_attr_{1} = {2}'.format(attr_type, self.type, self.get_column())

    def get_field_string(self):
        if self.fulltext and self.index_type != REAL_TIME_INDEX:
            return 'sql_field_string = {0}'.format(self.get_column())

        if self.index_type == REAL_TIME_INDEX and self.type == 'string':
            return 'rt_field = {0}'.format(self.get_column())

        return None

    def to_python(self, value):
        return value

    def __repr__(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path


class UIntField(Field):
    type = 'uint'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        return int(value)


class BoolField(Field):
    type = 'bool'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        return bool(value)


class BigIntegerField(UIntField):
    type = 'bigint'

    def to_python(self, value):
        return long(value)


class FloalField(Field):
    type = 'float'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        return float(value)


class TimeStamp(Field):
    type = 'timestamp'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        return datetime.datetime.fromtimestamp(value)


class StrToOrdinalField(Field):
    type = 'str2ordinal'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)
        raise NotImplementedError()

class MVAField(Field):
    type = 'multi'

    def __init__(self, *args, **kwargs):
        kwargs['stored'] = True
        Field.__init__(self, *args, **kwargs)
        raise NotImplementedError()
