# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Related'
        db.create_table('testapp_related', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('testapp', ['Related'])

        # Adding model 'M2M'
        db.create_table('testapp_m2m', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('testapp', ['M2M'])

        # Adding model 'Search'
        db.create_table('testapp_search', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('stored_string', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('bool', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('uint', self.gf('django.db.models.fields.IntegerField')()),
            ('excluded_field', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('excluded_field2', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('related', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['testapp.Related'])),
        ))
        db.send_create_signal('testapp', ['Search'])

        # Adding M2M table for field m2m on 'Search'
        db.create_table('testapp_search_m2m', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('search', models.ForeignKey(orm['testapp.search'], null=False)),
            ('m2m', models.ForeignKey(orm['testapp.m2m'], null=False))
        ))
        db.create_unique('testapp_search_m2m', ['search_id', 'm2m_id'])


    def backwards(self, orm):
        # Deleting model 'Related'
        db.delete_table('testapp_related')

        # Deleting model 'M2M'
        db.delete_table('testapp_m2m')

        # Deleting model 'Search'
        db.delete_table('testapp_search')

        # Removing M2M table for field m2m on 'Search'
        db.delete_table('testapp_search_m2m')


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
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'excluded_field': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'excluded_field2': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
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