import datetime
import logging
from optparse import make_option
import sys

from django.contrib.gis.geos import fromstr as geos_geom_from_string
from django.core.management.base import BaseCommand

import dateutil.parser
from lxml import etree
from lxml.builder import E

from open511.models import RoadEvent, Jurisdiction
from open511.utils.postgis import gml_to_ewkt
from open511.utils.serialization import ELEMENTS, XML_LANG, geom_to_xml_element

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-j', '--jurisdiction', action='store', dest='jurisdiction_slug',
            help='The slug of the jurisdiction to import items into.'),
    )

    element_lookup = dict(
        (e[1], e[0]) for e in ELEMENTS
    )

    def handle(self, filename=sys.stdin, **options):
        root = etree.parse(filename).getroot()
        assert root.tag == 'open511'

        created = []

        if options['jurisdiction_slug']:
            default_jurisdiction = Jurisdiction.objects.get(slug=options['jurisdiction_slug'])
        elif Jurisdiction.objects.filter(external_url='').count() == 1:
            default_jurisdiction = Jurisdiction.objects.get(external_url='')
        else:
            default_jurisdiction = None

        for event in root.xpath('roadEvent'):
            try:

                # Identify the jurisdiction
                external_jurisdiction = event.xpath('atom:link[rel=jurisdiction]',
                    namespaces=event.nsmap)
                if external_jurisdiction:
                    jurisdiction = Jurisdiction.objects.get(external_url=external_jurisdiction[0].text)
                    event.remove(external_jurisdiction[0])
                elif default_jurisdiction:
                    jurisdiction = default_jurisdiction
                else:
                    raise Exception("No jurisdiction provided")

                self_link = event.xpath('atom:link[rel=self]',
                    namespaces=event.nsmap)
                if self_link:
                    external_url = self_link[0].text
                    id = filter(None, external_url.split('/'))[-1]
                    event.remove(self_link[0])
                else:
                    external_url = ''
                    id = event.get('id')
                if not id:
                    raise Exception("No ID provided")

                try:
                    rdev = RoadEvent.objects.get(id=id, jurisdiction=jurisdiction)
                except RoadEvent.DoesNotExist:
                    rdev = RoadEvent(id=id, jurisdiction=jurisdiction, external_url=external_url)
                logger.info("Importing event %s" % rdev.id)

                # Extract the geometry
                geometry = event.xpath('geometry')[0]
                gml = etree.tostring(geometry[0])
                ewkt = gml_to_ewkt(gml, force_2D=True)
                rdev.geom = geos_geom_from_string(ewkt)

                # And regenerate the GML so it's consistent with the PostGIS representation
                event.remove(geometry)
                event.append(E.geometry(geom_to_xml_element(rdev.geom)))

                # Remove the ID from the stored XML (we keep it in the table)
                if 'id' in event.attrib:
                    del event.attrib['id']

                status = event.xpath('status')
                if status:
                    if status[0].text == 'archived':
                        rdev.active = False
                    event.remove(status[0])

                try:
                    created = event.xpath('creationDate/text()')[0]
                    created = dateutil.parser.parse(created)
                    if (not rdev.created) or created < rdev.created:
                        rdev.created = created
                except IndexError:
                    pass

                # Push down the default language if necessary
                if not event.get(XML_LANG):
                    event.set(XML_LANG, root.get(XML_LANG))

                rdev.xml_elem = event

                rdev.save()
                created.append(rdev)

            except ValueError as e:
                logger.error("ValueError importing %s: %s" % (e, rdev.id))

        print "%s entries imported." % len(created)


def _str_to_date(s):
    """2012-02-12 to a datetime.date object"""
    return datetime.date(*[
        int(x) for x in s.split('-')
    ])
