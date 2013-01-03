import json

from lxml import etree

GML_NS = 'http://www.opengis.net/gml'

def geojson_to_gml(gj):
    """Given a dict deserialized from a GeoJSON object, returns an lxml Element
    of the corresponding GML geometry."""
    if gj['type'] == 'Point':
        coords = ','.join(str(c) for c in gj['coordinates'])
    elif gj['type'] == 'LineString':
        coords = ' '.join(
            ','.join(str(c) for c in ll)
            for ll in gj['coordinates']
        )
    else:
        raise NotImplementedError
    tag = etree.Element('{%s}%s' % (GML_NS, gj['type']))
    coord_tag = etree.Element('{%s}coordinates' % GML_NS)
    coord_tag.text = coords
    tag.set('srsName', 'EPSG:4326')
    tag.append(coord_tag)
    return tag


def gml_to_geojson(el):
    """Given an lxml Element of a GML geometry, returns a dict in GeoJSON format."""
    coords = el.findtext('{%s}coordinates' % GML_NS)
    if el.tag.endswith('Point'):
        return {
            'type': 'Point',
            'coordinates': [float(c) for c in coords.split(',')]
        }
    elif el.tag.endswith('LineString'):
        return {
            'type': 'LineString',
            'coordinates': [
            [float(x) for x in pair.split(',')]
            for pair in coords.split(' ')
            ]
        }
    else:
        from open511.utils.postgis import pg_gml_to_geojson
        return json.loads(pg_gml_to_geojson(etree.tostring(el)))
