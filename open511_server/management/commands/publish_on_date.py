"""
To be executed in a cron job: finds all unpublished events with a
<protected:publish_on> date of today or earlier, and publishes
them.
"""

import datetime

from django.core.management.base import BaseCommand

from open511_server.models import RoadEvent
from open511_server.utils.serialization import NSMAP

class Command(BaseCommand):

    def handle(self, **options):

        count = 0

        for rdev in (RoadEvent.objects.filter(published=False)
                .extra(where=["(xpath('protected:publish_on/text()', xml_data, ARRAY[ARRAY['protected', 'http://open511.org/internal-namespace']]))[1]::text::date <= date %s"],
                params=[datetime.date.today()])):
            el = rdev.xml_elem.xpath('protected:publish_on', namespaces=NSMAP)[0]
            el.getparent().remove(el)
            rdev.published = True
            rdev.save()
            count += 1

        if count:
            print '%s event%s published' % (count, 's' if count > 1 else '')

