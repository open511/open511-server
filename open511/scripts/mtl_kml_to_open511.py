#coding: utf-8
"""
A script to convert Ville de Montreal roadwork KML files, e.g. from
http://depot.ville.montreal.qc.ca/info-travaux/data.kml
to an Open511 XML file.
"""

import datetime
import hashlib
import re
import sys

from django.contrib.gis.gdal import DataSource
from lxml import etree
from lxml.builder import E
import lxml.html

from open511.utils.serialization import (geom_to_xml_element, get_base_open511_element,
    ATOM_LINK)

ids_seen = set()


def feature_to_open511_element(feature):
    """Transform an OGR Feature from the KML input into an XML Element for a RoadEvent."""

    # Using a hash of the geometry for an ID. For proper production use,
    # there'll probably have to be some code in the importer
    # that compares to existing entries in the DB to determine whether
    # this is new or modified...
    id = hashlib.md5(feature.geom.wkt).hexdigest()
    while id in ids_seen:
        id += 'x'
    ids_seen.add(id)

    elem = E.roadEvent(id=id)

    def set_val(tag, val):
        if val not in (None, ''):
            e = etree.Element(tag)
            e.text = unicode(val)
            elem.append(e)

    set_val('status', 'active')
    set_val('eventType', 'Roadwork')

    set_val('headline', feature.get('Name').decode('utf8'))

    blob = lxml.html.fragment_fromstring(feature.get('Description').decode('utf8'),
        create_parent='content')

    description_label = blob.xpath('//strong[text()="Description"]')
    localisation = blob.cssselect('div#localisation p')
    if description_label or localisation:
        description_bits = []
        if description_label:
            el = description_label[0].getnext()
            while el.tag == 'p':
                description_bits.append(_get_el_text(el))
                el = el.getnext()

        if localisation:
            description_bits.append('Localisation: ' + '; '.join(
                _get_el_text(el) for el in localisation))

        set_val('description', '\n\n'.join(description_bits))

    try:
        url = blob.cssselect('#avis_residants a, #en_savoir_plus a')[0].get('href')
        e = etree.Element(ATOM_LINK)
        e.set('rel', 'related')
        e.set('href', url)
        elem.append(e)
    except IndexError:
        pass

    facultatif = blob.cssselect('div#itineraire_facult p')
    if facultatif:
        set_val('detour', '\n\n'.join(_get_el_text(el) for el in facultatif))

    if blob.cssselect('div#dates strong'):
        try:
            start_date = blob.xpath(u'div[@id="dates"]/strong[text()="Date de d\xe9but"]')[0].tail
            end_date = blob.xpath(u'div[@id="dates"]/strong[text()="Date de fin"]')[0].tail
            if start_date and end_date:
                elem.append(
                    E.schedule(
                        E.startDate(unicode(_fr_string_to_date(start_date))),
                        E.endDate(unicode(_fr_string_to_date(end_date))),
                    )
                )
        except IndexError:
            pass

    elem.append(E.geometry(
        geom_to_xml_element(feature.geom)
    ))

    return elem


def kml_file_to_open511_element(filename):
    """Transform a Montreal KML file, at filename, into an Element
    for the top-level <open511> element."""
    ds = DataSource(filename)
    base_element = get_base_open511_element(lang='fr')
    for layer in ds:
        for feature in layer:
            base_element.append(feature_to_open511_element(feature))
    return base_element


def _get_el_text(el):
    t = el.text if el.text else ''
    for subel in el:
        t += _get_el_text(subel)
        if subel.tail:
            t += subel.tail
    return t

FR_MONTHS = {
    'janvier': 1,
    u'février': 2,
    'mars': 3,
    'avril': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7,
    u'août': 8,
    'septembre': 9,
    'octobre': 10,
    'novembre': 11,
    u'décembre': 12
}

fr_date_re = re.compile(ur'(\d\d?) (%s) (\d{4})' % '|'.join(FR_MONTHS.keys()))


def _fr_string_to_date(s):
    match = fr_date_re.search(s)
    if not match:
        return None
    return datetime.date(
        int(match.group(3)),
        FR_MONTHS[match.group(2)],
        int(match.group(1))
    )


def main():
    filename = sys.argv[1]
    el = kml_file_to_open511_element(filename)
    print etree.tostring(el, pretty_print=True)

if __name__ == '__main__':
    main()
