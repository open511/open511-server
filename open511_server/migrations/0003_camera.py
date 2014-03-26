# encoding: utf8
from django.db import models, migrations
import open511_server.utils.xmlmodel
import django.contrib.gis.db.models.fields
import open511_server.fields
import open511_server.models


class Migration(migrations.Migration):

    dependencies = [
        ('open511', '0002_jurisdiction'),
    ]

    operations = [
        migrations.CreateModel(
            name='Camera',
            fields=[
                ('created', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('updated', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('internal_id', models.AutoField(serialize=False, primary_key=True)),
                ('id', models.CharField(db_index=True, max_length=100, blank=True)),
                ('jurisdiction', models.ForeignKey(to='open511.Jurisdiction', to_field='internal_id')),
                ('external_url', models.URLField(db_index=True, blank=True)),
                ('xml_data', open511_server.fields.XMLField(default='<camera xmlns:gml="http://www.opengis.net/gml" />')),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326, geography=True)),
            ],
            options={
                u'ordering': ('internal_id',),
                u'unique_together': set([('id', 'jurisdiction')]),
                u'abstract': False,
            },
            bases=(models.Model, open511_server.utils.xmlmodel.XMLModelMixin),
        ),
    ]
