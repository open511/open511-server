from collections import namedtuple
import json

from lxml import etree
from lxml.builder import E

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.utils.translation import ugettext_lazy as _

from open511.utils.http import DEFAULT_ACCEPT_LANGUAGE
from open511.utils.geojson import gml_to_geojson

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
ATOM_LINK = '{http://www.w3.org/2005/Atom}link'
GML_NS = 'http://www.opengis.net/gml'

NSMAP = {
    'gml': GML_NS,
    'atom': 'http://www.w3.org/2005/Atom'
}

try:
    DEFAULT_LANGUAGE = settings.LANGUAGE_CODE
except ImportError:
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

DataField = namedtuple('DataField', 'tag type name')
ELEMENTS = [
    DataField('headline', 'TEXT', _('Title')),
    DataField('event_type', 'CHAR', _('Event type')),
    DataField('description', 'TEXT', _('Description')),
    DataField('severity', 'CHAR', _('Severity')),
    DataField('traffic_restrictions', 'TEXT', _('Traffic Restrictions')),
    DataField('detour', 'TEXT', _('Detour')),
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

def make_link(rel, href):
    l = etree.Element(ATOM_LINK)
    l.set('rel', rel)
    l.set('href', href)
    return l

def xml_to_json(root):
    j = {}

    if isinstance(root, (list, tuple)):
        root = E.dummy(*root)

    if len(root) == 0:
        return root.text

    if len(root) == 1 and root[0].tag.startswith('{' + GML_NS):
        return gml_to_geojson(root[0])

    for elem in root:
        name = elem.tag
        if name == ATOM_LINK and elem.get('rel'):
            name = elem.get('rel') + '_url'
            if name == 'self_url':
                name = 'url'

        if name in j:
            continue  # duplicate
        elif elem.tag == ATOM_LINK and not elem.text:
            j[name] = elem.get('href')
        elif len(elem):
            # Is it a list of identical values?
            if all((name == child.tag + 's' for child in elem)):
                j[name] = [xml_to_json(child) for child in elem]
            else:
                j[name] = xml_to_json(elem)
        else:
            j[name] = elem.text

    return j

def json_to_xml(json_obj, root):
    if isinstance(root, basestring):
        root = etree.Element(root_name)
    for key, val in json_obj.items():
        if isinstance(val, dict):
            root.append(json_to_xml(val, key))
        elif val is not None:
            el = etree.Element(key)
            el.text = val
            root.append(el)
    return root



class XMLModelMixin(object):

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

