# encoding: utf8
from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('open511', '0003_camera'),
    ]

    operations = [
        migrations.CreateModel(
            name='JurisdictionGeography',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('jurisdiction', models.OneToOneField(to='open511.Jurisdiction', to_field='internal_id')),
                ('geom', django.contrib.gis.db.models.fields.GeometryField(srid=4326)),
            ],
            options={
                u'verbose_name_plural': 'Jurisdiction geographies',
            },
            bases=(models.Model,),
        ),
    ]
