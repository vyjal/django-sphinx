#coding: utf-8

from __future__ import unicode_literals

import re
import six
from bisect import bisect

# Calculate the verbose_name by converting from InitialCaps to "lowercase with underscores".
get_index_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', class_name).lower().strip('_')

#from djangosphinx.conf import SEARCHD_SETTINGS

__author__ = 'ego'

DEFAULT_OPTIONS = ('type', 'path', 'docinfo',
                   'morphology', 'charset_type',
                   'min_word_len', 'html_strip',
                    )

VALID_OPTIONS = dict(
    type=dict(
        type=six.string_types,
        values=('plain', 'distributed', 'rt'),
        default='plain',
    ),
    path=dict(
        type=six.string_types,
        default='/var/data/sphinx',
    ),
    docinfo=dict(
        type=six.string_types,
        values=('none', 'extern', 'inline'),
        default='extern',
    ),
    morphology=dict(
        type=six.string_types,
        values=('none', 'stem_en', 'stem_ru', 'stem_enru', 'stem_cz', 'soundex', 'metaphone'),
        default=None,
    ),
    dict=dict(
        type=six.string_types,
        values=('crc', 'keywords'),
        default='crc',
    ),
    charset_type=dict(
        type=six.string_types,
        values=('sdcs', 'utf-8'),
        default='utf-8',
    ),
    min_word_len=dict(
        type=int,
        default=3
    ),
    html_strip=dict(
        type=six.integer_types,
        values=(0, 1),
        default=1,
    ),
)

class Options(object):

    def __init__(self, meta):
        self.meta = meta

        self.object_name = None
        self.index_name = ''
        self.path = ''

        self.local_fields, self.local_sources = [], []

    def contribute_to_class(self, cls, name):

        cls._meta = self
        self.object_name = cls.__name__
        if hasattr(self.meta, 'index_name'):
            self.index_name = getattr(self.meta, 'index_name')
        else:
            self.index_name = get_index_name(self.object_name)

        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                if name.startswith('_'):
                    del meta_attrs[name]

            for attr_name in DEFAULT_OPTIONS:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))
                elif attr_name in VALID_OPTIONS and 'default' in VALID_OPTIONS[attr_name]:
                    setattr(self, attr_name, VALID_OPTIONS[attr_name]['default'])

        del self.meta


    def add_field(self, field):
        #print self.local_fields, field
        self.local_fields.insert(bisect(self.local_fields, field), field)

        if hasattr(self, '_field_cache'):
            del self._field_cache
            del self._field_name_cache

    def add_source(self, source):
        self.local_sources.insert(bisect(self.local_fields, source), source)

        if hasattr(self, '_source_cache'):
            del self._source_cache
            del self._source_name_cache

    def _fields(self):
        try:
            self._field_name_cache
        except AttributeError:
            cache = []

            cache.extend(self.local_fields)

            self._field_cache = tuple(cache)
            self._field_name_cache = tuple(cache)
        return self._field_name_cache

    fields = property(_fields)

    def _sources(self):
        try:
            self._source_cache
        except AttributeError:
            cache = []

            cache.extend(self.local_sources)

            self._source_cache = tuple(cache)
            self._source_name_cache = tuple(cache)

        return self._source_cache

    sources = property(_sources)

