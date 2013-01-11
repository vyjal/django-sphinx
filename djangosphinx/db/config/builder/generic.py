#coding: utf-8
from __future__ import unicode_literals

from djangosphinx.db.index.options import DEFAULT_OPTIONS
__author__ = 'ego'


class Builder(object):

    def __init__(self, model):
        self.model = model

    def build_source_config(self):
        sources = []
        for source in self.model._meta.sources:
            config = 'source {0} {{\n\t{1}\n}}\n'

            attrs = []
            for attr in ['type', 'sql_host', 'sql_port', 'sql_user', 'sql_pass', 'sql_db']:
                attrs.append('%s = %s' % (attr, getattr(source, attr)))

            sql_query_fields, sql_attrs, sql_fields = [], [], []
            for field in self.model._meta.fields:
                q = field.get_query_string()
                if q:
                    sql_query_fields.append(q)
                a = field.get_attr_string()
                if a:
                    sql_attrs.append(a)
                f = field.get_field_string()
                if f:
                    sql_fields.append(f)

    def build_index_config(self):
        config = 'index {0} {{\n\t{1}\n}}\n'

        attrs = []
        for opt_name in DEFAULT_OPTIONS:
            attrs.append('%s = %s' % (opt_name, getattr(self.model._meta, opt_name)))

        for source in self.model._meta.sources:
            attrs.append('source = %s' % source.name)

        return config.format(self.model._meta.index_name, '\n\t'.join(attrs))


