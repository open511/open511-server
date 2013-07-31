#coding: utf-8
"""
A script to scrape roadwork from the Québec transport ministry's
quebec511.gouv.qc.ca site into an Open511 XML file.
"""

import datetime
from itertools import chain
import logging
import json
import urllib, urllib2
import time

from django.contrib.gis.geos import Point

from lxml import etree
from lxml.builder import E
import lxml.html

from open511.utils.serialization import geom_to_xml_element, get_base_open511_element

logger = logging.getLogger(__name__)

ALL_QUEBEC_BOUNDS = {
    'xMin': '-79.9',
    'yMin': '44.4',
    'xMax': '-53.4',
    'yMax': '62.5'
}

BASE_LIST_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Element.ashx'
BASE_DETAIL_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Fenetres/FenetreTravailRoutier.aspx?id='

JURISDICTION_ID = 'mtq.scrapers.open511.org'

def get_list_of_chantiers(action='EntraveMajeure', bounds=ALL_QUEBEC_BOUNDS):
    params = {
        'action': action
    }
    params.update(bounds)

    url = BASE_LIST_URL + '?' + urllib.urlencode(params)

    resp = urllib2.urlopen(url)

    try:
        return json.load(resp)
    except ValueError as e:
        logger.error("Could not load JSON from %s: %r" % (url, e))
        return []


def get_roadevent_from_summary(summary):

    elem = E.event(E.id("%s/%s" % (JURISDICTION_ID, summary['id'])))

    elem.append(
        E.geography(
            geom_to_xml_element(
                Point(float(summary['lng']), float(summary['lat']), srid=4326)
            )
        )
    )

    url = BASE_DETAIL_URL + summary['id']
    resp = urllib2.urlopen(url)
    time.sleep(0.5)

    def set_val(tag, val):
        if val not in (None, ''):
            e = etree.Element(tag)
            e.text = unicode(val)
            elem.append(e)

    set_val('status', 'ACTIVE')
    set_val('event_type', 'CONSTRUCTION')
    set_val('severity', 'MAJOR' if summary['id'].startswith('maj') else 'MODERATE')

    root = lxml.html.fragment_fromstring(resp.read().decode('utf8'))
    set_val('headline', _get_text_from_elems(root.cssselect('#tdIdentification')))

    description = _get_text_from_elems(root.cssselect('#tdDescriptionEntrave,#tdDetail'))
    affected_roads = _get_text_from_elems(root.cssselect('#tdLocalisation'))
    traffic_restrictions = _get_text_from_elems(root.cssselect('#tdRestrictionCamionnage'))

    if affected_roads:
        description += u'\n\nLocalisation: ' + affected_roads
    if traffic_restrictions:
        description += u'\n\nRestrictions: ' + traffic_restrictions
    set_val('description', description)

    start_date = _get_text_from_elems(root.cssselect('#tdDebut'))
    end_date = _get_text_from_elems(root.cssselect('#tdFin'))
    if start_date or end_date:
        sked = E.schedule()
        if start_date:
            sked.append(E.start_date(unicode(_str_to_date(start_date))))
        if end_date:
            sked.append(E.end_date(unicode(_str_to_date(end_date))))
        elem.append(sked)

    return elem


def main():

    logging.basicConfig()

    base = get_base_open511_element(lang='fr')

    for summary in chain(
            get_list_of_chantiers(action='EntraveMajeure'),
            get_list_of_chantiers(action='EntraveMineure')):
        rdev = get_roadevent_from_summary(summary)
        base.append(rdev)

    print etree.tostring(base, pretty_print=True)


def _str_to_date(s):
    """2012-02-12 to a datetime.date object"""
    return datetime.date(*[
    int(x) for x in s.split('-')
    ])


def _get_text_from_elem(elem, include_tail=False):
    # Same as elem.text_content(), but replaces <br> with linebreaks
    return ''.join([
        (elem.text or ''),
        ('\n' if elem.tag == 'br' else ''),
        ''.join([_get_text_from_elem(e, True) for e in elem]),
        (elem.tail if elem.tail and include_tail else '')
    ])


def _get_text_from_elems(elems):
    return '\n\n'.join(_get_text_from_elem(e) for e in elems)

if __name__ == '__main__':
    main()
