# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Jurisdiction'
        db.create_table(u'open511_jurisdiction', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200, db_index=True)),
            ('external_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('xml_data', self.gf('open511.fields.XMLField')(default='<jurisdiction />')),
        ))
        db.send_create_signal(u'open511', ['Jurisdiction'])

        # Adding M2M table for field permitted_users on 'Jurisdiction'
        m2m_table_name = db.shorten_name(u'open511_jurisdiction_permitted_users')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('jurisdiction', models.ForeignKey(orm[u'open511.jurisdiction'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['jurisdiction_id', 'user_id'])

        # Adding model 'JurisdictionGeography'
        db.create_table(u'open511_jurisdictiongeography', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('jurisdiction', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['open511.Jurisdiction'], unique=True)),
            ('geom', self.gf('django.contrib.gis.db.models.fields.GeometryField')()),
        ))
        db.send_create_signal(u'open511', ['JurisdictionGeography'])

        # Adding model 'RoadEvent'
        db.create_table(u'open511_roadevent', (
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('internal_id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, blank=True)),
            ('jurisdiction', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['open511.Jurisdiction'])),
            ('severity', self.gf('django.db.models.fields.SmallIntegerField')(db_index=True, null=True, blank=True)),
            ('external_url', self.gf('django.db.models.fields.URLField')(db_index=True, max_length=200, blank=True)),
            ('geom', self.gf('django.contrib.gis.db.models.fields.GeometryField')(geography=True)),
            ('xml_data', self.gf('open511.fields.XMLField')(default='<event xmlns:atom="http://www.w3.org/2005/Atom" xmlns:gml="http://www.opengis.net/gml" />')),
        ))
        db.send_create_signal(u'open511', ['RoadEvent'])

        # Adding unique constraint on 'RoadEvent', fields ['id', 'jurisdiction']
        db.create_unique(u'open511_roadevent', ['id', 'jurisdiction_id'])

        # Adding model 'Area'
        db.create_table(u'open511_area', (
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 1, 0, 0))),
            ('geonames_id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('xml_data', self.gf('open511.fields.XMLField')(default='<area xmlns:atom="http://www.w3.org/2005/Atom" />')),
            ('geom', self.gf('django.contrib.gis.db.models.fields.GeometryField')(null=True, blank=True)),
            ('auto_label', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal(u'open511', ['Area'])


    def backwards(self, orm):
        # Removing unique constraint on 'RoadEvent', fields ['id', 'jurisdiction']
        db.delete_unique(u'open511_roadevent', ['id', 'jurisdiction_id'])

        # Deleting model 'Jurisdiction'
        db.delete_table(u'open511_jurisdiction')

        # Removing M2M table for field permitted_users on 'Jurisdiction'
        db.delete_table(db.shorten_name(u'open511_jurisdiction_permitted_users'))

        # Deleting model 'JurisdictionGeography'
        db.delete_table(u'open511_jurisdictiongeography')

        # Deleting model 'RoadEvent'
        db.delete_table(u'open511_roadevent')

        # Deleting model 'Area'
        db.delete_table(u'open511_area')


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
            'Meta': {'object_name': 'Area'},
            'auto_label': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
            'geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True', 'blank': 'True'}),
            'geonames_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
            'xml_data': ('open511.fields.XMLField', [], {'default': '\'<area xmlns:atom="http://www.w3.org/2005/Atom" />\''})
        },
        u'open511.jurisdiction': {
            'Meta': {'object_name': 'Jurisdiction'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
            'external_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permitted_users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
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
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
            'external_url': ('django.db.models.fields.URLField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'geography': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'internal_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['open511.Jurisdiction']"}),
            'severity': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 1, 0, 0)'}),
            'xml_data': ('open511.fields.XMLField', [], {'default': '\'<event xmlns:atom="http://www.w3.org/2005/Atom" xmlns:gml="http://www.opengis.net/gml" />\''})
        }
    }

    complete_apps = ['open511']