# encoding: utf8
from django.db import models, migrations
import open511_server.utils.serialization
import django.contrib.gis.db.models.fields
import open511_server.fields
import open511_server.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('created', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('updated', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('internal_id', models.AutoField(serialize=False, primary_key=True)),
                ('xml_data', open511_server.fields.XMLField(default='<area />')),
                ('geom', django.contrib.gis.db.models.fields.GeometryField(srid=4326, null=True, blank=True)),
                ('auto_label', models.BooleanField(default=False, help_text='Automatically include this Area in new events within its boundaries.', db_index=True)),
            ],
            options={
                u'abstract': False,
            },
            bases=(models.Model, open511_server.utils.serialization.XMLModelMixin),
        ),
    ]
