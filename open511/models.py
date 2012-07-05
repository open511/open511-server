from copy import deepcopy

from django.conf import settings
from django.contrib.gis.db import models
from django.core.serializers.json import simplejson as json
from django.utils.translation import ugettext_lazy as _

from lxml import etree

from open511.fields import XMLField
from open511.utils import serialization
from open511.utils.language import DEFAULT_ACCEPT

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


class RoadEvent(models.Model):

    internal_id = models.AutoField(primary_key=True)

    id = models.CharField(max_length=100, blank=True, db_index=True)
    jurisdiction = models.CharField(max_length=100, help_text=_('e.g. ville.montreal.qc.ca'),
        db_index=True)  # FK?

    geom = models.GeometryField(verbose_name=_('Geometry'))
    xml_data = XMLField(default='<RoadEvent />')

    class Meta(object):
        unique_together = [
            ('id', 'jurisdiction')
        ]

    def save(self, force_insert=False, force_update=False, using=None):
        self.xml_data = etree.tostring(self.xml_elem)
        self.full_clean()
        super(RoadEvent, self).save(force_insert=force_insert, force_update=force_update,
            using=using)
        if not self.id:
            mgr = RoadEvent._default_manager
            if using:
                mgr = mgr.using(using)
            mgr.filter(internal_id=self.internal_id).update(
                id=self.internal_id
            )

    @property
    def compound_id(self):
        return ':'.join([self.jurisdiction, self.id])

    __unicode__ = lambda s: s.compound_id

    def _get_elem(self):
        if not getattr(self, '_xml_elem', None):
            self._xml_elem = etree.fromstring(self.xml_data)
        return self._xml_elem

    def _set_elem(self, new_elem):
        self._xml_elem = new_elem

    xml_elem = property(_get_elem, _set_elem)

    @property
    # memoize?
    def default_lang(self):
        lang = self.xml_elem.get(XML_LANG)
        if not lang:
            lang = settings.LANGUAGE_CODE
        return lang

    def _get_text_elems(self, xpath):
        options = self.xml_elem.xpath(xpath)
        result = {}
        for option in options:
            lang = option.get(XML_LANG)
            if not lang:
                lang = self.default_lang
            result[lang] = option
        return result

    def get_text_value(self, name, accept=DEFAULT_ACCEPT):
        """Returns the text value with the given name, obeying language preferences.

        accept is a webob.acceptparse.AcceptLanguage object

        Returns None if no suitable value is found."""
        options = self._get_text_elems(name)
        best_language = accept.best_match(options.keys())
        if not best_language:
            return None
        return options[best_language].text

    def set_text_value(self, tagname, value, lang=settings.LANGUAGE_CODE):
        existing = self._get_text_elems(tagname)
        if lang in existing:
            elem = existing[lang]
        else:
            elem = etree.Element(tagname)
            if lang != self.default_lang:
                elem.set(XML_LANG, lang)
            self.xml_elem.append(elem)
        elem.text = value

    def to_json_structure(self, accept=DEFAULT_ACCEPT):
        r = {
            'id': self.id,
            'jurisdiction': self.jurisdiction,
            'Geometry': json.loads(self.geom.geojson)
        }
        for field in serialization.ELEMENTS:
            if field.type == 'TEXT':
                val = self.get_text_value(field.tag, accept=accept)
            else:
                val = self.xml_elem.xpath(field.tag + '/text()')
                val = val[0] if val else None
            if val not in [None, '']:
                r[field.tag] = val
        return r

    def to_full_xml_element(self):
        el = deepcopy(self.xml_elem)
        geom = etree.Element('Geometry')
        geom.append(serialization.geom_to_xml_element(self.geom))
        el.append(geom)
        el.set('id', self.compound_id)
        return el
