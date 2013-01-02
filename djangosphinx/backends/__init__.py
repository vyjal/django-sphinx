#coding: utf-8
from __future__ import  absolute_import

__author__ = 'ego'

from django.conf import settings
from .base import decimal

backend = getattr(settings, 'SPHINX_BACKEND', 'mysql')

if backend == 'mysql':
    from .mysql import SphinxQuerySet
elif backend == 'api':
    from .api import SphinxQuerySet
else:
    raise Exception('Unknown Sphinx backend `%s`' % backend)

__all__ = ['decimal', 'SphinxQuerySet']