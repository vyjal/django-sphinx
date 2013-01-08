# coding: utf-8
from __future__ import unicode_literals

from django.db import models
import itertools

__all__ = ['all_indexes', 'sphinx_query']

_all_sphinx_indexes_cache = None


def all_indexes():
    global _all_sphinx_indexes_cache
    if _all_sphinx_indexes_cache is None:
        indexes = []
        model_classes = itertools.chain(*(models.get_models(app) for app in models.get_apps()))
        for model in model_classes:
            if getattr(model._meta, 'proxy', False) or getattr(model._meta, 'abstract', False):
                continue
            index = getattr(model, '__sphinx_indexes__', None)
            if index is not None:
                indexes.extend(index)
        _all_sphinx_indexes_cache = ' '.join(indexes)
    return _all_sphinx_indexes_cache
