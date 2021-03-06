from __future__ import print_function

import logging
from optparse import make_option
import re
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from django.core.exceptions import (ValidationError, ImproperlyConfigured)
from django.core.management.base import BaseCommand
from django.db import transaction

from lxml import etree
import requests

from open511.utils.serialization import XML_LANG, XML_BASE
from open511.validator import Open511ValidationError

from open511_server.conf import settings
from open511_server.models import RoadEvent, Jurisdiction, Camera


logger = logging.getLogger(__name__)

RESOURCE_TYPES = [
    {'container': 'events', 'objects': 'events/event', 'model': RoadEvent},
    {'container': 'cameras', 'objects': 'cameras/camera', 'model': Camera}
]

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', type=str, help='Path or URL to the Open511 data to import')
        parser.add_argument('--archive', action='store_true', dest='archive',
            help='Set the status of all events in the jurisdiction *not* in the supplied file to ARCHIVED.')
        parser.add_argument('--quiet', action='store_true',
            help="Don't print any messages unless there's an error.")

    @transaction.atomic
    def handle(self, source, **options):
        logging.basicConfig()

        source_is_url = bool(re.search(r'^https?://', source))
        root = self.fetch_from_url(source) if source_is_url else etree.parse(source).getroot()
        assert root.tag == 'open511'

        created = []

        opts = {}

        resource_type = next(t for t in RESOURCE_TYPES if root.xpath(t['container']))

        if options['archive']:
            if resource_type['model'] != RoadEvent:
                raise Exception("The archive option works only with road events")
            jurisdiction_ids = set(eid.split('/')[0] for eid in root.xpath('events/event/id/text()'))
            if len(jurisdiction_ids) > 1:
                raise ImproperlyConfigured(
                    "To use the archive option, all events must belong to the same jurisdiction.")
            if not jurisdiction_ids:
                raise Exception("Are there events in this file?")
            archive_jurisdiction_id = jurisdiction_ids.pop()

        if root.get(XML_LANG):
            opts['default_language'] = root.get(XML_LANG)

        if root.get(XML_BASE):
            opts['base_url'] = root.get(XML_BASE)
        elif source_is_url:
            opts['base_url'] = source

        while True:
            # Loop until we've dealt with all pages

            for xml_obj in root.xpath(resource_type['objects']):
                try:
                    _, db_obj = resource_type['model'].objects.update_or_create_from_xml(xml_obj, **opts)
                    logger.info("Imported %s %s" % (xml_obj.tag, db_obj.id))

                    created.append(db_obj)

                except (ValueError, ValidationError, Open511ValidationError) as e:
                    logger.error("%s importing %s: %s" % (e.__class__.__name__, xml_obj.findtext('id'), e))

            next_link = root.xpath('pagination/link[@rel="next"]')
            if not next_link:
                break
            if not source_is_url:
                logger.warning("File contains a next link but was loaded from local filesystem; "
                    "not following the link. If you want to fetch other pages, use the URL of the "
                    "first page as the argument to this command.")
                break
            next_url = urljoin(source, next_link[0].get('href'))
            root = self.fetch_from_url(next_url)

        msg = "%s entries imported." % len(created)

        if options['archive'] and created:
            archive_jurisdiction = Jurisdiction.objects.get(id=archive_jurisdiction_id)
            updated = RoadEvent.objects.filter(jurisdiction=archive_jurisdiction, active=True).exclude(
                id__in=[rdev.id for rdev in created]).update(active=False)
            msg += " %s events archived." % updated

        if not options['quiet']:
            print(msg)

    def fetch_from_url(self, url):
        resp = requests.get(url, headers={
            'Accept': 'application/xml; */*;q=0.1',
            'Open511-Version': settings.OPEN511_DEFAULT_VERSION
        })
        return etree.fromstring(resp.content)
