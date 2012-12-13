from lxml.etree import Element

from open511.utils.serialization import GML_NS

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
    tag = Element('{%s}%s' % (GML_NS, gj['type']))
    coord_tag = Element('{%s}coordinates' % GML_NS)
    coord_tag.text = coords
    tag.set('srsName', 'EPSG:4326')
    tag.append(coord_tag)
    return tag
