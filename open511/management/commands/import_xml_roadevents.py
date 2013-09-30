import logging
from optparse import make_option
import re
import sys
import urllib2

from django.core.exceptions import (ValidationError, ImproperlyConfigured)
from django.core.management.base import BaseCommand

from lxml import etree

from open511.models import RoadEvent, Jurisdiction
from open511.utils.serialization import XML_LANG, XML_BASE

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--archive', action='store_true', dest='archive',
            help='Set the status of all events in the jurisdiction *not* in the supplied file to ARCHIVED.'),
    )

    def handle(self, source, **options):
        if re.search(r'^https?://', source):
            source_url = source
            source = urllib2.urlopen(source_url)
        root = etree.parse(source).getroot()
        assert root.tag == 'open511'

        created = []

        opts = {}
        if options['archive']:
            jurisdiction_ids = set(eid.split('/')[0] for eid in root.xpath('event/id/text()'))
            if len(jurisdiction_ids) > 1:
                raise ImproperlyConfigured(
                    "To use the archive option, all events must belong to the same jurisdiction.")
            archive_jurisdiction_id = jurisdiction_ids.pop()

        if root.get(XML_LANG):
            opts['default_language'] = root.get(XML_LANG)

        if root.get(XML_BASE):
            opts['base_url'] = root.get(XML_BASE)

        for event in root.xpath('events/event'):
            try:
                rdev = RoadEvent.objects.update_or_create_from_xml(event, **opts)
                logger.info("Imported event %s" % rdev.id)

                created.append(rdev)

            except (ValueError, ValidationError) as e:
                logger.error("%s importing %s: %s" % (e.__class__.__name__, event.get('id'), e))

        msg = "%s entries imported." % len(created)

        if options['archive']:
            archive_jurisdiction = Jurisdiction.objects.get(id=archive_jurisdiction_id)
            updated = RoadEvent.objects.filter(jurisdiction=archive_jurisdiction).exclude(
                id__in=[rdev.id for rdev in created]).update(active=False)
            msg += " %s events archived." % updated

        print msg
