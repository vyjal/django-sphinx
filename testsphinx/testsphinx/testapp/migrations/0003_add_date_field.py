# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Search.date'
        db.add_column('testapp_search', 'date',
                      self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2012, 12, 30, 0, 0)),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Search.date'
        db.delete_column('testapp_search', 'date')


    models = {
        'testapp.m2m': {
            'Meta': {'object_name': 'M2M'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'testapp.related': {
            'Meta': {'object_name': 'Related'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'testapp.search': {
            'Meta': {'object_name': 'Search'},
            'bool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'excluded_field': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'excluded_field2': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'float': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'm2m': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['testapp.M2M']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'related': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['testapp.Related']"}),
            'stored_string': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'uint': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['testapp']