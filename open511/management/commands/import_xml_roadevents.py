import logging
import sys

from django.contrib.gis.geos import fromstr as geos_geom_from_string
from django.core.management.base import BaseCommand, CommandError

from lxml import etree

from open511.models import RoadEvent
from open511.utils.postgis import gml_to_ewkt
from open511.utils.serialization import ELEMENTS

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    element_lookup = dict(
        (e[1], e[0]) for e in ELEMENTS
    )

    def handle(self, filename = sys.stdin, **options):
        root = etree.parse(filename).getroot()
        assert root.tag == 'Open511'

        created = []

        for event in root.xpath('RoadEvent'):
            try:
                rdev = RoadEvent(source_id=event.get('id'))
                logger.info("Importing event %s" % rdev.source_id)
                rdev.jurisdiction = rdev.source_id.split(':')[0]

                for event_el in event:
                    if event_el.tag in self.element_lookup:
                        setattr(rdev, self.element_lookup[event_el.tag], event_el.text)
                    elif event_el.tag == 'Geometry':
                        gml = etree.tostring(event_el[0])
                        ewkt = gml_to_ewkt(gml, force_2D=True)
                        rdev.geom = geos_geom_from_string(ewkt)
                    else:
                        logger.warning("Unknown tag: %s" % etree.tostring(event_el))

                rdev.save()
                created.append(rdev)

            except ValueError as e:
                logger.error("ValueError importing %s: %s" % (e, rdev.source_id))

        print "%s entries imported." % len(created)



