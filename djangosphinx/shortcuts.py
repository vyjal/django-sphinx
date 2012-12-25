from djangosphinx.models import SphinxQuerySet
from django.db import models
import itertools

__all__ = ('sphinx_query',)

_all_sphinx_indexes_cache = None


def _all_indexes():
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


def sphinx_query(query):
    qs = SphinxQuerySet(index=_all_indexes())
    return qs.query(query)
