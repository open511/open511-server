from collections import namedtuple
from copy import deepcopy
import re

from lxml import etree
from lxml.builder import E

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

import open511_validator

from open511.utils.http import DEFAULT_ACCEPT_LANGUAGE
from open511.utils.geojson import gml_to_geojson

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
GML_NS = 'http://www.opengis.net/gml'

NSMAP = {
    'gml': GML_NS,
    'protected': 'http://open511.org/namespaces/internal-field'
}

try:
    DEFAULT_LANGUAGE = settings.LANGUAGE_CODE
except (ImportError, ImproperlyConfigured):
    DEFAULT_LANGUAGE = 'en'

etree.register_namespace('gml', GML_NS)
parser = etree.XMLParser(remove_blank_text=True)

def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if isinstance(geom, GEOSGeometry):
        geom = geom.ogr
    xml = '<geom xmlns:gml="http://www.opengis.net/gml">%s</geom>' % geom.gml
    el = etree.fromstring(xml)
    return el[0]


def gml2_to_gml3(gml_string, remove_3D=True):
    """Transform a string representation of a GMLv2 geometry to a GMLv3 geometry.
    (Or rather, since GMLv3 is backwards compatible, substitute deprecated elements
        with their GMLv3 equivalents.)"""
    assert gml_string.startswith('<gml:')
    if gml_string.startswith('<gml:Point') or gml_string.startswith('<gml:MultiPoint'):
        gml_string = gml_string.replace('gml:coordinates', 'gml:pos')
    else:
        gml_string = gml_string.replace('gml:coordinates', 'gml:posList')
    if gml_string.startswith('<gml:Polygon') or gml_string.startswith('<gml:MultiPolygon'):
        gml_string = gml_string.replace('gml:outerBoundaryIs', 'gml:exterior').replace('gml:innerBoundaryIs', 'gml:interior')
    if remove_3D:
        gml_string = re.sub(r',0(?=[ <])', '', gml_string)
    return gml_string.replace(',', ' ')

DataField = namedtuple('DataField', 'tag type name')
ELEMENTS = [
    DataField('headline', 'TEXT', _('Title')),
    DataField('event_type', 'CHAR', _('Event type')),
    DataField('description', 'TEXT', _('Description')),
    DataField('severity', 'CHAR', _('Severity')),
    DataField('traffic_restrictions', 'TEXT', _('Traffic Restrictions')),
    DataField('detour', 'TEXT', _('Detour')),
    DataField('road_name', 'TEXT', _('Road name')),
    DataField('to', 'TEXT', _('To')),
    DataField('from', 'TEXT', _('From')),
    DataField('name', 'TEXT', _('Name')),
]

ELEMENTS_LOOKUP = dict((f.tag, f) for f in ELEMENTS)

def get_base_open511_element(lang=None, base=None):
    elem = etree.Element("open511", nsmap={
        'gml': 'http://www.opengis.net/gml',
    })
    if lang:
        elem.set(XML_LANG, lang)
    if base:
        elem.set(XML_BASE, base)
    return elem

def make_link(rel, href):
    l = etree.Element('link')
    l.set('rel', rel)
    l.set('href', href)
    return l

def xml_link_to_json(link, to_dict=False):
    if to_dict:
        d = {'url': link.get('href')}
        for attr in ('type', 'title', 'length'):
            if link.get(attr):
                d[attr] = link.get(attr)
        return d
    else:
        return link.get('href')

def json_link_to_xml(val, rel='related'):
    tag = etree.Element('link')
    tag.set('rel', rel)
    if hasattr(val, 'get') and 'url' in val:
        tag.set('href', val['url'])
        for attr in ('type', 'title', 'length'):
            if val.get(attr):
                tag.set(attr, unicode(val[attr]))
    else:
        tag.set('href', val)
    return tag

def _maybe_intify(t):
    return int(t) if hasattr(t, 'isdigit') and t.isdigit() else t

def xml_to_json(root):
    j = {}

    if isinstance(root, (list, tuple)):
        root = E.dummy(*root)

    if len(root) == 0:
        return _maybe_intify(root.text)

    if len(root) == 1 and root[0].tag.startswith('{' + GML_NS):
        return gml_to_geojson(root[0])

    for elem in root:
        name = elem.tag
        if name == 'link' and elem.get('rel'):
            name = elem.get('rel') + '_url'
            if name == 'self_url':
                name = 'url'
        elif name.startswith('{' + NSMAP['protected']):
            name = '!' + name[name.index('}') + 1:] 
        elif name[0] == '{':
            # Namespace!
            name = '+' + name[name.index('}') + 1:]

        if name in j:
            continue  # duplicate
        elif elem.tag == 'link' and not elem.text:
            j[name] = elem.get('href')
        elif len(elem):
            if name in ('attachments', 'grouped_events'):
                j[name] = [xml_link_to_json(child, to_dict=(name == 'attachments')) for child in elem]
            elif all((name == child.tag + 's' for child in elem)):
                # <something><somethings> serializes to a JSON array
                j[name] = [xml_to_json(child) for child in elem]
            else:
                j[name] = xml_to_json(elem)
        else:
            j[name] = _maybe_intify(elem.text)

    return j


def json_to_xml(json_obj, root):
    if isinstance(root, basestring):
        if root.startswith('!'):
            root = etree.Element('{%s}%s' % (NSMAP['protected'], root[1:]))
        else:
            root = etree.Element(root)
    if root.tag in ('attachments', 'grouped_events'):
        for link in json_obj:
            root.append(json_link_to_xml(link))
    elif isinstance(json_obj, basestring):
        root.text = json_obj
    elif isinstance(json_obj, dict):
        for key, val in json_obj.items():
            el = json_to_xml(val, key)
            if el is not None:
                root.append(el)
    elif isinstance(json_obj, list):
        tag_name = root.tag
        if tag_name.endswith('s'):
            tag_name = tag_name[:-1]
        for val in json_obj:
            el = json_to_xml(val, tag_name)
            if el is not None:
                root.append(el)
    elif json_obj is None:
        return None
    else:
        raise NotImplementedError
    return root


class CannotChooseLanguageError(Exception):
    pass


class XMLModelMixin(object):

    # This must be a list of tag names that contain potentially multilingual content.
    # The order is important: the *first* tag should be a required element, and is
    # used to determine which languages a given piece of data contains.
    FREE_TEXT_TAGS = []

    def _get_elem(self):
        if getattr(self, '_xml_elem', None) is None:
            self._xml_elem = etree.fromstring(self.xml_data, parser=parser)
        return self._xml_elem

    def _set_elem(self, new_elem):
        self._xml_elem = new_elem

    xml_elem = property(_get_elem, _set_elem)

    @property
    # memoize?
    def default_lang(self):
        lang = self.xml_elem.get(XML_LANG)
        if not lang:
            lang = DEFAULT_LANGUAGE
        return lang

    def _get_text_elems(self, xpath, root=None):
        if root is None:
            root = self.xml_elem
        options = root.xpath(xpath)
        result = {}
        for option in options:
            lang = option.get(XML_LANG)
            if not lang:
                lang = self.default_lang
            result[lang] = option
        return result

    def get_text_value(self, name, accept=DEFAULT_ACCEPT_LANGUAGE):
        """Returns the text value with the given name, obeying language preferences.

        accept is a webob.acceptparse.AcceptLanguage object

        Returns None if no suitable value is found."""
        options = self._get_text_elems(name)
        best_language = accept.best_match(options.keys())
        if not best_language:
            return None
        return options[best_language].text

    def set_text_value(self, tagname, value, lang=DEFAULT_LANGUAGE):
        existing = self._get_text_elems(tagname)
        if lang in existing:
            elem = existing[lang]
        else:
            elem = etree.Element(tagname)
            if lang != self.default_lang:
                elem.set(XML_LANG, lang)
            self.xml_elem.append(elem)
        if value:
            elem.text = value
        else:
            self.xml_elem.remove(elem)

    def set_tag_value(self, tagname, value):
        existing = self.xml_elem.xpath(tagname)
        assert len(existing) < 2
        if existing:
            el = existing[0]
        else:
            el = etree.Element(tagname)
            self.xml_elem.append(el)
        if value in (None, ''):
            self.xml_elem.remove(el)
        else:
            el.text = unicode(value)

    def _determine_best_language(self, accept=DEFAULT_ACCEPT_LANGUAGE):
        """Given Accept-Language options, determine what the best language is
        to return this event in.

        accept - a webob AcceptLanguage object"""
        if not self.FREE_TEXT_TAGS:
            raise CannotChooseLanguageError("No list of free-text tags")
        test_tag = self.FREE_TEXT_TAGS[0]
        languages = self._get_text_elems(test_tag, self.xml_elem).keys()
        if not languages:
            raise CannotChooseLanguageError("%s is required" % test_tag)
        best_match = accept.best_match(languages, default_match=None)
        if best_match:
            return best_match
        if settings.LANGUAGE_CODE in languages:
            # If we don't have a good Accept-Language match,
            # try and return the default language.
            return settings.LANGUAGE_CODE
        # Failing everything else, return what we have.
        return languages[0]

    def _prune_languages(self, parent, lang):
        """Remove all free-text elements that don't match the provided language."""
        rejects = set()
        for child in parent:
            if len(child):
                self._prune_languages(child, lang)
            elif (child not in rejects and child.tag in self.FREE_TEXT_TAGS):
                options = self._get_text_elems(child.tag, root=parent)
                rejects |= set(o for l, o in options.items() if l != lang)
        for reject in rejects:
            parent.remove(reject)

    def remove_unnecessary_languages(self, accept_language, elem=None):
        if not accept_language:
            return elem if elem is not None else self.xml_elem
        if elem is None:
            elem = deepcopy(self.xml_elem)
        lang = self._determine_best_language(accept_language)
        self._prune_languages(elem, lang)
        return elem

    def validate_xml(self):
        # First, create a full XML doc to validate
        doc = get_base_open511_element()
        if hasattr(self, 'get_validation_xml'):
            doc.append(self.get_validation_xml())
        else:
            doc.append(self.xml_elem)
        doc.extend([
            make_link('self', '/'),
            make_link('up', '/')
        ])
        doc.set('version', 'v0')
        # Then run it through schema
        open511_validator.validate(doc)
