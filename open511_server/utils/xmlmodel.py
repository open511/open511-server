from copy import deepcopy

from lxml import etree

from open511.validator import validate
from open511.converter import pluralize
from open511.utils.serialization import GML_NS, XML_LANG, get_base_open511_element

from open511_server.utils.http import DEFAULT_ACCEPT_LANGUAGE

ImproperlyConfigured = None
try:
    from django.core.exceptions import ImproperlyConfigured
    from open511_server.conf import settings
    DEFAULT_LANGUAGE = settings.LANGUAGE_CODE
    DEFAULT_VERSION = settings.OPEN511_DEFAULT_VERSION
except (ImportError, ImproperlyConfigured):
    DEFAULT_LANGUAGE = 'en'
    DEFAULT_VERSION = 'v0'

etree.register_namespace('gml', GML_NS)
parser = etree.XMLParser(remove_blank_text=True)

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
        el = self.get_validation_xml() if hasattr(self, 'get_validation_xml') else self.xml_elem
        container = etree.Element(pluralize(el.tag))
        container.append(el)
        doc.append(container)
        doc.set('version', settings.OPEN511_DEFAULT_VERSION)
        # Then run it through schema
        validate(doc)
