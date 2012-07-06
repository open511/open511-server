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
import lxml.html

from open511.utils.serialization import roadevent_to_xml_element, get_base_open511_element

logger = logging.getLogger(__name__)

ALL_QUEBEC_BOUNDS = {
    'xMin': '-79.9',
    'yMin': '44.4',
    'xMax': '-53.4',
    'yMax': '62.5'
}

JURISDICTION = 'converted.quebec511.gouv.qc.ca'

BASE_LIST_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Element.ashx'
BASE_DETAIL_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Fenetres/FenetreTravailRoutier.aspx?id='

class DummyRoadEvent(object):
    pass

def get_list_of_chantiers(action='EntraveMajeure', bounds=ALL_QUEBEC_BOUNDS):
    params = {
        'action': action
    }
    params.update(bounds)

    url = BASE_LIST_URL + '?' + urllib.urlencode(params)

    resp = urllib2.urlopen(url)

    try: 
      json_data = json.load(resp)
    except ValueError:
      print('Value error in the JSON load - Probably an invalid JSON feed\n')
      json_data = '' 

    return json_data

def get_roadevent_from_summary(summary):

    rdev = DummyRoadEvent()
    rdev.source_id = JURISDICTION + ':' + summary['id']

    #rdev.title = summary['info']
    rdev.geom = Point(float(summary['lng']), float(summary['lat']), srid=4326)

    url = BASE_DETAIL_URL + summary['id']
    resp = urllib2.urlopen(url)
    time.sleep(1)

    root = lxml.html.fragment_fromstring(resp.read().decode('utf8'))
    rdev.title = _get_text_from_elems(root.cssselect('#tdIdentification'))
    rdev.description = _get_text_from_elems(root.cssselect('#tdDescriptionEntrave,#tdDetail'))
    rdev.affected_roads = _get_text_from_elems(root.cssselect('#tdLocalisation'))
    rdev.traffic_restrictions = _get_text_from_elems(root.cssselect('#tdRestrictionCamionnage'))

    start_date = _get_text_from_elems(root.cssselect('#tdDebut'))
    end_date = _get_text_from_elems(root.cssselect('#tdFin'))
    if start_date:
        rdev.start_date = _str_to_date(start_date)
    if end_date:
        rdev.end_date = _str_to_date(end_date)

    return rdev

def main():

    base = get_base_open511_element()

    for summary in chain(
            get_list_of_chantiers(action='EntraveMajeure'),
            get_list_of_chantiers(action='EntraveMineure')):
        rdev = get_roadevent_from_summary(summary)
        elem = roadevent_to_xml_element(rdev)
        base.append(elem)

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






