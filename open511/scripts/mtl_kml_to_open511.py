#coding: utf-8
"""
A script to convert Ville de Montreal roadwork KML files, e.g. from
http://depot.ville.montreal.qc.ca/info-travaux/data.kml
to an Open511 XML file.
"""

import datetime
import hashlib
import os
import re
import sys
import tempfile
import urllib2

from django.contrib.gis.gdal import DataSource
from lxml import etree
from lxml.builder import E
import lxml.html

from open511.utils.serialization import (geom_to_xml_element, get_base_open511_element)

ids_seen = set()

SOURCE_URL = 'http://depot.ville.montreal.qc.ca/info-travaux/data.kml'
JURISDICTION_ID = 'montreal.scrapers.open511.org'


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

    elem = E.event()

    def set_val(tag, val):
        if val not in (None, ''):
            e = etree.Element(tag)
            e.text = unicode(val)
            elem.append(e)

    def maybe_decode(s):
        if isinstance(s, unicode):
            return s
        return s.decode('utf8')

    set_val('id', "%s/%s" % (JURISDICTION_ID, id))
    set_val('status', 'ACTIVE')
    set_val('event_type', 'CONSTRUCTION')
    set_val('severity', 'UNKNOWN')

    set_val('headline', maybe_decode(feature.get('Name')))

    blob = lxml.html.fragment_fromstring(maybe_decode(feature.get('Description')),
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
        link = blob.cssselect('#avis_residants a, #en_savoir_plus a')[0]
        e = etree.Element('link')
        e.set('rel', 'related')
        e.set('href', link.get('href'))
        if link.get('title'):
            e.set('title', link.get('title'))
        elem.append(E.attachments(e))
    except IndexError:
        pass

    facultatif = blob.cssselect('div#itineraire_facult p')
    if facultatif:
        set_val('detour', '\n\n'.join(_get_el_text(el) for el in facultatif))

    if blob.cssselect('div#dates strong'):
        try:
            start_date = blob.xpath(u'div[@id="dates"]/strong[text()="Date de d\xe9but"]')[0].tail
            end_date = blob.xpath(u'div[@id="dates"]/strong[text()="Date de fin"]')[0].tail
            start_date = _fr_string_to_date(start_date)
            end_date = _fr_string_to_date(end_date)
            if start_date:
                sked = E.schedule(E.start_date(unicode(start_date)))
                if end_date:
                    sked.append(E.end_date(unicode(end_date)))
                elem.append(sked)
        except IndexError:
            pass

    elem.append(E.geography(
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
    if not s:
        return None
    match = fr_date_re.search(s)
    if not match:
        return None
    return datetime.date(
        int(match.group(3)),
        FR_MONTHS[match.group(2)],
        int(match.group(1))
    )

def download_file():
    resp = urllib2.urlopen(SOURCE_URL)
    descriptor, filename = tempfile.mkstemp(suffix='.kml')
    f = os.fdopen(descriptor, 'w')
    f.write(resp.read())
    f.close()
    return filename

def main():
    filename = sys.argv[1]
    dl = filename == 'download'
    if dl: filename = download_file()
    el = kml_file_to_open511_element(filename)
    if dl: os.unlink(filename)
    print etree.tostring(el, pretty_print=True)

if __name__ == '__main__':
    main()
