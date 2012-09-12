from copy import deepcopy

from django.conf import settings
from django.contrib.gis.db import models
from django.core import urlresolvers
from django.core.serializers.json import simplejson as json
from django.utils.translation import ugettext_lazy as _

from lxml import etree

from open511.fields import XMLField
from open511.utils.serialization import ELEMENTS, geom_to_xml_element, XML_LANG, ATOM_LINK
from open511.utils.language import DEFAULT_ACCEPT


class _Open511Model(models.Model):

    @property
    def url(self):
        if getattr(self, 'external_url', None):
            return self.external_url
        return self.get_absolute_url()

    @property
    def full_url(self):
        url = self.url
        if url.startswith('/'):
            return settings.OPEN511_BASE_URL + url
        return url

    class Meta(object):
        abstract = True


class Jurisdiction(_Open511Model):

    slug = models.SlugField()
    name = models.CharField(max_length=500)

    external_url = models.URLField(blank=True)

    xml_data = XMLField(default='<jurisdiction />')

    def __unicode__(self):
        return self.slug

    def get_absolute_url(self):
        return urlresolvers.reverse('open511_jurisdiction', kwargs={'slug': self.slug})

class RoadEvent(_Open511Model):

    internal_id = models.AutoField(primary_key=True)

    id = models.CharField(max_length=100, blank=True, db_index=True)
    jurisdiction = models.ForeignKey(Jurisdiction)

    external_url = models.URLField(blank=True, db_index=True)

    geom = models.GeometryField(verbose_name=_('Geometry'))
    xml_data = XMLField(default='<roadEvent />')

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

    def __unicode__(self):
        return u"%s (%s)" % (self.id, self.jurisdiction)

    def get_absolute_url(self):
        return urlresolvers.reverse('open511_roadevent', kwargs={
            'jurisdiction_slug': self.jurisdiction.slug,
            'id': self.id}
        )

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

    def to_json_structure(self, accept=DEFAULT_ACCEPT):
        r = {
            'id': self.id,
            'jurisdiction': self.jurisdiction,
            'Geometry': json.loads(self.geom.geojson)
        }
        for field in ELEMENTS:
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
        geom.append(geom_to_xml_element(self.geom))
        el.append(geom)

        link = etree.Element(ATOM_LINK)
        link.set('rel', 'jurisdiction')
        link.set('href', self.jurisdiction.full_url)
        el.insert(0, link)

        link = etree.Element(ATOM_LINK)
        link.set('rel', 'self')
        link.set('href', self.url)
        el.insert(0, link)

        return el

    # method to return full XML element conforming to language list
    # option: return ALL languages matching accept list?
    # option: return BEST option in all cases

    @property
    def headline(self):
        return self.get_text_value('headline')
