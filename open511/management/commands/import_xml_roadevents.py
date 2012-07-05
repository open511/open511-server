import datetime
import logging
import sys

from django.contrib.gis.geos import fromstr as geos_geom_from_string
from django.core.management.base import BaseCommand

from lxml import etree

from open511.models import RoadEvent, XML_LANG
from open511.utils.postgis import gml_to_ewkt
from open511.utils.serialization import ELEMENTS

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    element_lookup = dict(
        (e[1], e[0]) for e in ELEMENTS
    )

    def handle(self, filename=sys.stdin, **options):
        root = etree.parse(filename).getroot()
        assert root.tag == 'Open511'

        created = []

        for event in root.xpath('RoadEvent'):
            try:
                jurisdiction, dummy, id = event.get('id').partition(':')
                try:
                    rdev = RoadEvent.objects.get(id=id, jurisdiction=jurisdiction)
                except RoadEvent.DoesNotExist:
                    rdev = RoadEvent(id=id, jurisdiction=jurisdiction)
                logger.info("Importing event %s" % rdev.id)

                # Extract the geometry
                geometry = event.xpath('Geometry')[0]
                gml = etree.tostring(geometry[0])
                ewkt = gml_to_ewkt(gml, force_2D=True)
                rdev.geom = geos_geom_from_string(ewkt)
                event.remove(geometry)

                # Remove the ID from the stored XML (we keep it in the table)
                del event.attrib['id']

                # Push down the default language if necessary
                if not event.get(XML_LANG):
                    event.set(XML_LANG, root.get(XML_LANG))

                rdev.xml_elem = event

                rdev.save()
                created.append(rdev)

            except ValueError as e:
                logger.error("ValueError importing %s: %s" % (e, rdev.compound_id))

        print "%s entries imported." % len(created)


def _str_to_date(s):
    """2012-02-12 to a datetime.date object"""
    return datetime.date(*[
        int(x) for x in s.split('-')
    ])
