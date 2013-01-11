#coding: utf-8

from __future__ import absolute_import
from __future__ import unicode_literals

__author__ = 'ego'

from .options import Options

class IndexBase(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(IndexBase, cls).__new__
        parents = [b for b in bases if isinstance(b, IndexBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)

        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        base_meta = getattr(new_class, '_meta', None)

        new_class.add_to_class('_meta', Options(meta))

        # Можно переопределить тип индекса, унаследовав его
        # эт чтобы дважды не описывать одно и то же
        if base_meta:
            if not hasattr(meta, 'type'):
                new_class._meta.type = base_meta.type

        #print attrs

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        return new_class

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

class Index(object):
    __metaclass__ = IndexBase
