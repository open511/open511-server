from collections import namedtuple

from lxml import etree

from django.contrib.gis.geos import GEOSGeometry

try:
    import simplejson as json
except ImportError:
    import json

etree.register_namespace('gml', 'http://www.opengis.net/gml')


def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if isinstance(geom, GEOSGeometry):
        geom = geom.ogr
    xml = '<geom xmlns:gml="http://www.opengis.net/gml">%s</geom>' % geom.gml
    el = etree.fromstring(xml)
    return el[0]

DataField = namedtuple('DataField', 'tag type')
ELEMENTS = [
    DataField('Title', 'TEXT'),
    DataField('EventType', 'CHAR'),
    DataField('AffectedRoads', 'TEXT'),
    DataField('Description', 'TEXT'),
    DataField('Severity', 'CHAR'),
    DataField('TrafficRestrictions', 'TEXT'),
    DataField('Detour', 'TEXT'),
    DataField('ExternalURL', 'CHAR'),
    DataField('StartDate', 'DATE'),
    DataField('EndDate', 'DATE'),
]


def get_base_open511_element(lang=None):
    elem = etree.Element("Open511", nsmap={
        'gml': 'http://www.opengis.net/gml'
    })
    if lang:
        elem.set('{http://www.w3.org/XML/1998/namespace}lang', lang)
    return elem
