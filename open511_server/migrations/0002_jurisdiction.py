# encoding: utf8
from django.db import models, migrations
import open511_server.utils.serialization
from django.conf import settings
import open511_server.fields
import open511_server.models


class Migration(migrations.Migration):

    dependencies = [
        ('open511', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Jurisdiction',
            fields=[
                ('created', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('updated', models.DateTimeField(default=open511_server.models._now, db_index=True)),
                ('internal_id', models.AutoField(serialize=False, primary_key=True)),
                ('id', models.CharField(unique=True, max_length=100, db_index=True)),
                ('external_url', models.URLField(blank=True)),
                ('xml_data', open511_server.fields.XMLField(default='<jurisdiction />')),
                ('permitted_users', models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True)),
            ],
            options={
                u'abstract': False,
            },
            bases=(models.Model, open511_server.utils.serialization.XMLModelMixin),
        ),
    ]
