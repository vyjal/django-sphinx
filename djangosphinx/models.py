# coding: utf-8

import warnings

from djangosphinx.backends import *


class SphinxModelManager(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self._index = kwargs.pop('index', model._meta.db_table)
        self._kwargs = kwargs

    def _get_query_set(self):
        return SphinxQuerySet(self.model, index=self._index, **self._kwargs)

    def get_index(self):
        return self._index

    def all(self):
        return self._get_query_set()

    def none(self):
        return self._get_query_set().none()

    def filter(self, **kwargs):
        return self._get_query_set().filter(**kwargs)

    def query(self, *args, **kwargs):
        return self._get_query_set().query(*args, **kwargs)


'''
class SphinxInstanceManager(object):
    """Collection of tools useful for objects which are in a Sphinx index."""
    # TODO: deletion support
    def __init__(self, instance, index):
        self._instance = instance
        self._index = index

    def update(self, **kwargs):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use UpdateAttributes."
        sphinxapi.UpdateAttributes(self._index, kwargs.keys(), dict(self.instance.pk, map(to_sphinx, kwargs.values())))
'''

class SphinxSearch(object):
    def __init__(self, index=None, using=None, **kwargs):
        # Metadata for things like excluded_fields, included_fields, etc
        try:
            self._options = kwargs.pop('options')
        except:
            self._options = None

        self._kwargs = kwargs
        self._sphinx = None
        self._index = index

        self.model = None
        self.using = using

    def __call__(self, index, **kwargs):
        warnings.warn('For non-model searches use a SphinxQuerySet instance.', DeprecationWarning)
        return SphinxQuerySet(index=index, using=self.using, **kwargs)

    #def __get__(self, instance, model, **kwargs):
    #    if instance:
    #        return SphinxInstanceManager(instance, self._index)
    #    return self._sphinx

    def get_query_set(self):
        """Override this method to change the QuerySet used for config generation."""
        return self.model._default_manager.all()

    def contribute_to_class(self, model, name, **kwargs):
        if self._index is None:
            self._index = model._meta.db_table
        self._sphinx = SphinxModelManager(model, index=self._index, **self._kwargs)
        self.model = model

        if hasattr(model, '__sphinx_indexes__') or hasattr(model, '__sphinx_options__'):
            raise AttributeError('Only one instance of SphinxSearch can be present in the model: `%s.%s`' % (self.model._meta.app_label, self.model._meta.object_name))

        setattr(model, '__sphinx_indexes__', [self._index])
        setattr(model, '__sphinx_options__', self._options)

        setattr(model, name, self._sphinx)


