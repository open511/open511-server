from lxml import etree
from lxml.builder import E

from django.contrib.gis.geos import GEOSGeometry

try:
    import simplejson as json
except ImportError:
    import json

def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if isinstance(geom, GEOSGeometry):
        geom = geom.ogr
    xml = '<geom xmlns:gml="http://www.opengis.net/gml">%s</geom>' % geom.gml
    el = etree.fromstring(xml)
    return el[0]

ELEMENTS = [
    ('title', 'Title'),
    ('type', 'EventType'),
    ('affected_roads', 'AffectedRoads'),
    ('description', 'Description'),
    ('severity', 'Severity'),
    ('closed', 'Closed'),
    ('traffic_restrictions', 'TrafficRestrictions'),
    ('detour', 'Detour'),
    ('external_url', 'ExternalURL'),
    ('start_date', 'StartDate'),
    ('end_date', 'EndDate'),
]

def roadevent_to_xml_element(rdev):
    """Transform a RoadEvent object, or something which duck-typily looks
    similar, into an lxml <RoadEvent> Element."""
    base = E.RoadEvent(id=rdev.source_id)

    for attr, el_name in ELEMENTS:
        val = getattr(rdev, attr, None)
        if val not in (None, ''):
            el = etree.Element(el_name)
            el.text = unicode(val)
            base.append(el)

    base.append(E.Geometry(geom_to_xml_element(rdev.geom)))
    return base

def roadevent_to_json_structure(rdev):
    base = {
        'id': rdev.source_id
    }

    for attr, el_name in ELEMENTS:
        val = getattr(rdev, attr, None)
        if val not in (None, ''):
            base[el_name] = unicode(val)

    base['Geometry'] = json.loads(rdev.geom.geojson)
    return base

def get_base_open511_element():
    return etree.Element("Open511", nsmap={
        'gml': 'http://www.opengis.net/gml'
    })