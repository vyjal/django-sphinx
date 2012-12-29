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
    bool = models.BooleanField()
    uint = models.IntegerField()

    excluded_field = models.CharField(max_length=10)
    excluded_field2 = models.CharField(max_length=10)

    related = models.ForeignKey(Related)
    m2m = models.ManyToManyField(M2M)

    search = SphinxSearch(
        options={
            'included_fields': [
                'name',
                'text',

                'datetime',
                'bool',
                'uint',
            ],
            'stored_attributes': [
                'stored_string',
            ],
            'related_fields': [
                'related',
            ],
            'mva_fields': [
                'm2m',
            ]
        },
        passages=True,
    )

    def __unicode__(self):
        return self.name
