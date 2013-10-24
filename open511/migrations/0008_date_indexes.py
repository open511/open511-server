# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Area', fields ['updated']
        db.create_index(u'open511_area', ['updated'])

        # Adding index on 'Area', fields ['created']
        db.create_index(u'open511_area', ['created'])

        # Adding index on 'RoadEvent', fields ['updated']
        db.create_index(u'open511_roadevent', ['updated'])

        # Adding index on 'RoadEvent', fields ['created']
        db.create_index(u'open511_roadevent', ['created'])

        # Adding index on 'Jurisdiction', fields ['updated']
        db.create_index(u'open511_jurisdiction', ['updated'])

        # Adding index on 'Jurisdiction', fields ['created']
        db.create_index(u'open511_jurisdiction', ['created'])


    def backwards(self, orm):
        # Removing index on 'Jurisdiction', fields ['created']
        db.delete_index(u'open511_jurisdiction', ['created'])

        # Removing index on 'Jurisdiction', fields ['updated']
        db.delete_index(u'open511_jurisdiction', ['updated'])

        # Removing index on 'RoadEvent', fields ['created']
        db.delete_index(u'open511_roadevent', ['created'])

        # Removing index on 'RoadEvent', fields ['updated']
        db.delete_index(u'open511_roadevent', ['updated'])

        # Removing index on 'Area', fields ['created']
        db.delete_index(u'open511_area', ['created'])

        # Removing index on 'Area', fields ['updated']
        db.delete_index(u'open511_area', ['updated'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'open511.area': {
            'Meta': {'ordering': "['created']", 'object_name': 'Area'},
            'auto_label': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True', 'blank': 'True'}),
            'geonames_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'xml_data': ('open511.fields.XMLField', [], {'default': "'<area />'"})
        },
        u'open511.jurisdiction': {
            'Meta': {'ordering': "['created']", 'object_name': 'Jurisdiction'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'external_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'internal_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permitted_users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'xml_data': ('open511.fields.XMLField', [], {'default': "'<jurisdiction />'"})
        },
        u'open511.jurisdictiongeography': {
            'Meta': {'object_name': 'JurisdictionGeography'},
            'geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['open511.Jurisdiction']", 'unique': 'True'})
        },
        u'open511.roadevent': {
            'Meta': {'unique_together': "[('id', 'jurisdiction')]", 'object_name': 'RoadEvent'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'external_url': ('django.db.models.fields.URLField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'geography': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'internal_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['open511.Jurisdiction']"}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 30, 0, 0)', 'db_index': 'True'}),
            'xml_data': ('open511.fields.XMLField', [], {'default': '\'<event xmlns:gml="http://www.opengis.net/gml" />\''})
        }
    }

    complete_apps = ['open511']