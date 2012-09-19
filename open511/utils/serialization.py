from collections import namedtuple

from lxml import etree

from django.contrib.gis.geos import GEOSGeometry
from django.utils.translation import ugettext_lazy as _

try:
    import simplejson as json
except ImportError:
    import json

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
ATOM_LINK = '{http://www.w3.org/2005/Atom}link'

etree.register_namespace('gml', 'http://www.opengis.net/gml')


def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if isinstance(geom, GEOSGeometry):
        geom = geom.ogr
    xml = '<geom xmlns:gml="http://www.opengis.net/gml">%s</geom>' % geom.gml
    el = etree.fromstring(xml)
    return el[0]

DataField = namedtuple('DataField', 'tag type name')
ELEMENTS = [
    DataField('headline', 'TEXT', _('Title')),
    DataField('eventType', 'CHAR', _('Event type')),
    DataField('description', 'TEXT', _('Description')),
    DataField('severity', 'CHAR', _('Severity')),
    DataField('trafficRestrictions', 'TEXT', _('Traffic Restrictions')),
    DataField('detour', 'TEXT', _('Detour')),
    DataField('ExternalURL', 'CHAR', _('External URL')),
    DataField('StartDate', 'DATE', _('Start date')),
    DataField('EndDate', 'DATE', _('End date')),
]

ELEMENTS_LOOKUP = dict((f.tag, f) for f in ELEMENTS)

def get_base_open511_element(lang=None, base=None):
    elem = etree.Element("open511", nsmap={
        'gml': 'http://www.opengis.net/gml',
        'atom': 'http://www.w3.org/2005/Atom'
    })
    if lang:
        elem.set(XML_LANG, lang)
    if base:
        elem.set(XML_BASE, base)
    return elem


def xml_to_json(root):
    j = {}

    for elem in root:
        name = elem.tag
        if name == ATOM_LINK and elem.get('rel'):
            name = elem.get('rel')
            if name == 'self':
                name = 'url'

        if name in j:
            continue  # duplicate

        if name.lower() == 'geometry':
            # We can probably implement this ourselves & make it much more efficient
            # (& get rid of the postgis dependency)
            from open511.utils.postgis import gml_to_geojson
            j[name] = json.loads(gml_to_geojson(etree.tostring(elem[0])))
        elif elem.tag == ATOM_LINK and not elem.text:
            j[name] = elem.get('href')
        elif len(elem):
            # Is it a simple list of values?
            if all((child.tag == name + 's' and len(child) == 0 for child in elem)):
                j[name] = [child.text for child in elem]
            else:
                j[name] = xml_to_json(elem)
        else:
            j[name] = elem.text

    return j



