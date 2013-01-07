# coding: utf-8

from django.db import models
from djangosphinx.models import SphinxSearch
# Create your models here.

__all__ = ['Related', 'M2M', 'Search']

class Related(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

class M2M(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name


class Search(models.Model):

    name = models.CharField(max_length=10)
    text = models.TextField()
    stored_string = models.CharField(max_length=100)

    datetime = models.DateTimeField()
    date = models.DateField()
    bool = models.BooleanField()
    uint = models.IntegerField()
    float = models.FloatField(default=1.0)

    excluded_field = models.CharField(max_length=10)
    excluded_field2 = models.CharField(max_length=10)

    related = models.ForeignKey(Related)
    m2m = models.ManyToManyField(M2M)

    search = SphinxSearch(
        options={
            'realtime': True,
            'included_fields': [
                'text',

                'datetime',
                'bool',
                'uint',
            ],
            'excluded_fields': [
                'excluded_field2',
            ],
            'stored_attributes': [
                'stored_string',
            ],
            'stored_fields': [
                'excluded_field',
            ],
            'related_fields': [
                'related',
            ],
            'mva_fields': [
                'm2m',
            ]
        },
        snippets=True,
    )

    def __unicode__(self):
        return self.name

# Пример неправильной модели

"""
class DoubleSphinxSearch(models.Model):

    name = models.CharField(max_length=10)

    search1 = SphinxSearch()
    search2 = SphinxSearch()
"""

class FakeSphinxClient(object):
    def __init__(self, *args, **kwargs):
        pass

    def SetSerner(*args, **kwargs):
        pass

    def BuildExcerpts(self, *args, **kwargs):
        return []
