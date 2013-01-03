import logging
from optparse import make_option
import re
import sys
import urllib2

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from lxml import etree

from open511.models import RoadEvent, Jurisdiction
from open511.utils.serialization import XML_LANG, XML_BASE

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-j', '--jurisdiction', action='store', dest='jurisdiction_slug',
            help='The slug of the jurisdiction to import items into.'),
    )

    def handle(self, source, **options):
        if re.search(r'^https?://', source):
            source_url = source
            source = urllib2.urlopen(source_url)
        root = etree.parse(source).getroot()
        assert root.tag == 'open511'

        created = []

        if options['jurisdiction_slug']:
            default_jurisdiction = Jurisdiction.objects.get(slug=options['jurisdiction_slug'])
        elif Jurisdiction.objects.filter(external_url='').count() == 1:
            default_jurisdiction = Jurisdiction.objects.get(external_url='')
        else:
            default_jurisdiction = None

        opts = {
            'default_jurisdiction': default_jurisdiction
        }
        if root.get(XML_LANG):
            opts['default_language'] = root.get(XML_LANG)

        if root.get(XML_BASE):
            opts['base_url'] = root.get(XML_BASE)

        for event in root.xpath('roadEvent'):
            try:
                rdev = RoadEvent.objects.update_or_create_from_xml(event, **opts)
                logger.info("Imported event %s" % rdev.id)

                created.append(rdev)

            except (ValueError, ValidationError) as e:
                logger.error("%s importing %s: %s" % (e.__class__.__name__, event.get('id'), e))

        print "%s entries imported." % len(created)

