from copy import deepcopy
import datetime
from urlparse import urljoin

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.geos import fromstr as geos_geom_from_string
from django.core import urlresolvers
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import utc

import dateutil.parser
import hashlib
from lxml import etree
from lxml.builder import E
import requests
import pytz

from open511.fields import XMLField
from open511.utils import is_hex
from open511.utils.cache import memoize_method
from open511.utils.calendar import Schedule
from open511.utils.geojson import geojson_to_ewkt
from open511.utils.postgis import gml_to_ewkt
from open511.utils.serialization import (
    geom_to_xml_element, XML_LANG, XMLModelMixin, NSMAP,
    json_to_xml, make_link
)


def _now():
    return datetime.datetime.now(utc).replace(microsecond=0)  # microseconds == overkill

class _Open511Model(models.Model):

    created = models.DateTimeField(default=_now)
    updated = models.DateTimeField(default=_now)

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

    def save(self, *args, **kwargs):
        self.updated = _now()
        return super(_Open511Model, self).save(*args, **kwargs)

    class Meta(object):
        abstract = True


class JurisdictionManager(models.GeoManager):

    def get_or_create_from_url(self, url):
        try:
            return self.get(external_url=url)
        except ObjectDoesNotExist:
            slug = filter(None, url.split('/'))[-1]
            try:
                return self.get(slug=slug)
            except ObjectDoesNotExist:
                pass

        # Looks like we need to fetch the jurisdiction
        req = requests.get(url, headers={'Accept': 'application/xml'})
        root = etree.fromstring(req.content)
        jur = root.xpath('jurisdiction')[0]
        jur_id = jur.xpath('id/text()')[0]
        
        try:
            return self.get(slug=jur_id)
        except ObjectDoesNotExist:
            return self.update_or_create_from_xml(jur, base_url=url)

    def update_or_create_from_xml(self, xml_jurisdiction, base_url=None):
        xml_jurisdiction = deepcopy(xml_jurisdiction)
        jur_id = xml_jurisdiction.xpath('id/text()')[0]
        self_link = xml_jurisdiction.xpath('link[@rel="self"]',
            namespaces=NSMAP)[0]
        if not base_url:
            base_url = self_link.get('href')
        try:
            jur = self.get(slug=jur_id)
        except ObjectDoesNotExist:
            jur = self.model(
                external_url=self_link.get('href'),
                slug=jur_id
            )
            try:
                created = xml_jurisdiction.xpath('created/text()')[0]
                jur.created = dateutil.parser.parse(created)
            except IndexError:
                pass

        for path in ['status', 'created', 'updated', 'link[@rel="self"]', 'id']:
            for elem in xml_jurisdiction.xpath(path, namespaces=NSMAP):
                xml_jurisdiction.remove(elem)
        for link in xml_jurisdiction.xpath('link', namespaces=NSMAP):
            if not link.get('href').startswith('http'):
                # If the link isn't absolute, make it so
                link.set('href', urljoin(base_url, link.get('href')))
        jur.xml_elem = xml_jurisdiction
        jur.save()
        return jur

    def get_default_timezone_for(self, id):
        # FIXME cache
        return self.get(pk=id).default_timezone


class Jurisdiction(_Open511Model, XMLModelMixin):

    slug = models.CharField(max_length=200, unique=True, db_index=True)

    external_url = models.URLField(blank=True)

    # geom = models.MultiPolygonField(blank=True, null=True)

    xml_data = XMLField(default='<jurisdiction />')

    permitted_users = models.ManyToManyField(User, blank=True)

    objects = JurisdictionManager()

    FREE_TEXT_TAGS = ['name', 'description']

    def __unicode__(self):
        return self.slug

    def get_absolute_url(self):
        return urlresolvers.reverse('open511_jurisdiction', kwargs={'slug': self.slug})

    def save(self, force_insert=False, force_update=False, using=None):
        self.xml_data = etree.tostring(self.xml_elem)
        self.full_clean()
        super(Jurisdiction, self).save(force_insert=force_insert, force_update=force_update,
            using=using)

    def to_full_xml_element(self, accept_language=None):
        el = deepcopy(self.xml_elem)

        el.insert(0, make_link('self', self.full_url))
        el.insert(0, E.id(self.slug))

        # el.append(E.created(self.created.isoformat()))
        # el.append(E.updated(self.updated.isoformat()))

        if (
                not el.xpath('link[@rel="geography"]', namespaces=NSMAP)
                and JurisdictionGeography.objects.filter(jurisdiction=self).exists()):
            el.append(make_link('geography', self.get_absolute_url() + 'geography/'))

        self.remove_unnecessary_languages(accept_language, el)

        return el

    @property
    def name(self):
        return self.get_text_value('name')

    @property
    def default_timezone(self):
        tzname = self.xml_elem.findtext('timezone')
        return pytz.timezone(tzname) if tzname else None

    def can_edit(self, user):
        return self.permitted_users.filter(id=user.id).exists()


class JurisdictionGeography(models.Model):

    jurisdiction = models.OneToOneField(Jurisdiction)

    geom = models.GeometryField()

    objects = models.GeoManager()

    class Meta:
        verbose_name_plural = 'Jurisdiction geographies'

    def __unicode__(self):
        return u"Geography for %s" % self.jurisdiction

    def get_absolute_url(self):
        return self.jurisdiction.get_absolute_url() + 'geography/'

    def to_full_xml_element(self):
        return E.geography(geom_to_xml_element(self.geom))


class RoadEventManager(models.GeoManager):

    def update_or_create_from_xml(self, event,
            default_jurisdiction=None, default_language=settings.LANGUAGE_CODE, base_url=''):
        # Identify the jurisdiction
        event = deepcopy(event)
        external_jurisdiction = event.xpath('link[@rel="jurisdiction"]',
            namespaces=NSMAP)
        if external_jurisdiction:
            jurisdiction = Jurisdiction.objects.get_or_create_from_url(external_jurisdiction[0].get('href'))
            event.remove(external_jurisdiction[0])
        elif default_jurisdiction:
            jurisdiction = default_jurisdiction
        else:
            raise Exception("No jurisdiction provided")

        self_link = event.xpath('link[@rel="self"]',
            namespaces=NSMAP)
        if self_link:
            external_url = urljoin(base_url, self_link[0].get('href'))
            id = filter(None, external_url.split('/'))[-1]
            event.remove(self_link[0])
        else:
            external_url = ''
            id = event.get('id')
        if not id:
            raise Exception("No ID provided")

        try:
            rdev = self.get(id=id, jurisdiction=jurisdiction)
        except RoadEvent.DoesNotExist:
            rdev = self.model(id=id, jurisdiction=jurisdiction, external_url=external_url)

        # Extract the geometry
        geometry = event.xpath('geography')[0]
        gml = etree.tostring(geometry[0])
        ewkt = gml_to_ewkt(gml, force_2D=True)
        rdev.geom = geos_geom_from_string(ewkt)

        # And regenerate the GML so it's consistent with the PostGIS representation
        event.remove(geometry)
        event.append(E.geography(geom_to_xml_element(rdev.geom)))

        # Remove the ID from the stored XML (we keep it in the table)
        if 'id' in event.attrib:
            del event.attrib['id']

        status = event.xpath('status')
        if status:
            if status[0].text.lower() == 'archived':
                rdev.active = False

        try:
            created = event.xpath('created/text()')[0]
            created = dateutil.parser.parse(created)
            if (not rdev.created) or created < rdev.created:
                rdev.created = created
        except IndexError:
            pass

        for path in ['status', 'created', 'updated']:
            for elem in event.xpath(path):
                event.remove(elem)

        # Push down the default language if necessary
        if not event.get(XML_LANG):
            event.set(XML_LANG, default_language)

        rdev.xml_elem = event
        rdev.save()
        return rdev


class RoadEvent(_Open511Model, XMLModelMixin):

    internal_id = models.AutoField(primary_key=True)
    active = models.BooleanField(default=True)

    id = models.CharField(max_length=100, blank=True, db_index=True)
    jurisdiction = models.ForeignKey(Jurisdiction)
    severity = models.SmallIntegerField(blank=True, null=True, db_index=True)

    published = models.BooleanField(default=True, db_index=True)

    external_url = models.URLField(blank=True, db_index=True)

    geom = models.GeometryField(verbose_name=_('Geometry'), geography=True)
    xml_data = XMLField(
        default='<event xmlns:gml="http://www.opengis.net/gml" />')

    objects = RoadEventManager()

    FREE_TEXT_TAGS = [
        'headline', 'description', 'detour', 'road_name', 'from', 'to', 'area_name'
    ]

    class Meta(object):
        unique_together = [
            ('id', 'jurisdiction')
        ]

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop('lang', settings.LANGUAGE_CODE)
        super(RoadEvent, self).__init__(*args, **kwargs)
        if not self.internal_id and not self.xml_elem.get(XML_LANG):
            self.xml_elem.set(XML_LANG, lang)

    def save(self, force_insert=False, force_update=False, using=None):
        self.xml_data = etree.tostring(self.xml_elem)
        self.full_clean()
        try:
            self.severity = int(self.xml_elem.xpath('severity/text()')[0])
        except (IndexError, ValueError):
            pass
        super(RoadEvent, self).save(force_insert=force_insert, force_update=force_update,
            using=using)
        if not self.id:
            mgr = RoadEvent._default_manager
            if using:
                mgr = mgr.using(using)
            mgr.filter(internal_id=self.internal_id).update(
                id=self.internal_id
            )
            self.id = self.internal_id

    def __unicode__(self):
        return u"%s (%s)" % (self.id, self.jurisdiction)

    def clean(self):
        self.validate_xml()

    def get_absolute_url(self):
        return urlresolvers.reverse('open511_roadevent', kwargs={
            'jurisdiction_slug': self.jurisdiction.slug,
            'id': self.id}
        )

    def get_validation_xml(self):
        return self.to_full_xml_element(fake_links=True)

    def to_full_xml_element(self, accept_language=None,
            fake_links=False, remove_internal_elements=False):
        el = deepcopy(self.xml_elem)

        el.insert(0, E.status('ACTIVE' if self.active else 'ARCHIVED'))

        if fake_links:
            el.insert(0, make_link('jurisdiction', '/xxx'))
            el.insert(0, make_link('self', '/xxx/yyy'))
        else:
            el.insert(0, make_link('jurisdiction', self.jurisdiction.full_url))
            el.insert(0, make_link('self', self.url))

        el.append(E.created(self.created.isoformat()))
        el.append(E.updated(self.updated.isoformat()))

        if remove_internal_elements:
            for internal_element in el.xpath('//*[namespace-uri()="' + NSMAP['protected'] + '"]'):
                internal_element.getparent().remove(internal_element)
        else:
            if not self.published:
                unpublished = etree.Element('{%s}unpublished' % NSMAP['protected'], nsmap=NSMAP)
                unpublished.text = 'true'
                el.append(unpublished)

        self.remove_unnecessary_languages(accept_language, el)

        return el

    def _get_or_create_el(self, path, parent=None):
        if parent is None:
            parent = self.xml_elem
        xpath_query = path
        if path[0] == '!':
            xpath_query = 'protected:' + path[1:]
        els = parent.xpath(xpath_query, namespaces=NSMAP)
        if len(els) == 1:
            return els[0]
        elif not els:
            if '/' in path:
                raise NotImplementedError
            elif path[0] == '!':
                path = '{' + NSMAP['protected'] + '}' + path[1:]
                el = etree.Element(path, nsmap=NSMAP)
            else:
                el = etree.Element(path)
            parent.append(el)
            return el
        elif len(els) > 1:
            raise NotImplementedError

    def update(self, key, val):

        if key in ('updated', 'created'):
            raise NotImplementedError
        elif key == 'status':
            self.active = (val.upper() == 'ACTIVE')
            return
        elif key == '!unpublished':
            self.published = (not val) or unicode(val).lower() == 'false'
            return
        elif key.startswith('_'):
            # ignore internal fields
            return

        update_el = self._get_or_create_el(key)

        if val is None:
            update_el.getparent().remove(update_el)
        elif isinstance(val, basestring):
            update_el.text = val
        elif key == 'geography':
            if 'opengis' in getattr(val, 'tag', ''):
                wkt = gml_to_ewkt(etree.tostring(val))
            else:
                wkt = geojson_to_ewkt(val)
            self.geom = geos_geom_from_string(wkt)
            update_el.clear()
            update_el.append(geom_to_xml_element(self.geom))
        elif isinstance(val, (dict, list)):
            if not val:
                update_el.getparent().remove(update_el)
            update_el.clear()
            json_to_xml(val, update_el)
        else:
            raise NotImplementedError

    @property
    def headline(self):
        return self.get_text_value('headline')

    @property
    def schedule(self):
        sched = self.xml_elem.find('schedule')
        if sched is None:
            raise ValidationError("Schedule is required")
        return Schedule(sched,
            default_timezone=Jurisdiction.objects.get_default_timezone_for(self.jurisdiction_id))

    def auto_label_areas(self):
        """Based on geometry, include any matching Areas we know about."""
        areas = Area.objects.filter(auto_label=True, geom__intersects=self.geom)
        for area in areas:
            if self.xml_elem.xpath('areas/area/area_id[text()="%s"]' % area.geonames_id):
                continue
            try:
                areas_el = self.xml_elem.xpath('areas')[0]
            except IndexError:
                areas_el = E.areas()
                self.xml_elem.append(areas_el)
            areas_el.append(area.xml_elem)


class Area(_Open511Model, XMLModelMixin):

    geonames_id = models.IntegerField(primary_key=True)

    xml_data = XMLField(default='<area />')

    geom = models.GeometryField(blank=True, null=True)

    auto_label = models.BooleanField(default=False, db_index=True,
        help_text="Automatically include this Area in new events within its boundaries.")

    objects = models.GeoManager()

    FREE_TEXT_TAGS = ['area_name']

    @property
    def name(self):
        return self.get_text_value('name')

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.geonames_id)

    def save(self, *args, **kwargs):
        if not self.xml_elem.xpath('area_id'):
            self.xml_elem.insert(0, E.area_id(str(self.geonames_id)))
            self.xml_elem.append(make_link('self', 'http://geonames.org/%s/about.rdf' % self.geonames_id))
        self.xml_data = etree.tostring(self.xml_elem)
        self.full_clean()
        super(Area, self).save(*args, **kwargs)


class SearchGeometry(object):
    """A saved geometry object, to be used in searches."""

    DoesNotExist = ObjectDoesNotExist

    def __init__(self, geom, id):
        self.id = id
        self.geom = geom

    def save(self):
        if self.id is None:
            self.id = hashlib.md5(self.geom.wkt).hexdigest()
        cache.set('searchgeometry_%s' % self.id, 
            self.geom, 60*60*24) # FIXME configurable duration

    @staticmethod
    def get(key):
        obj = cache.get('searchgeometry_%s' % key)
        if obj is None:
            raise SearchGeometry.DoesNotExist
        else:
            return SearchGeometry(obj, id=key)

    @classmethod
    def fromstring(cls, input):
        if is_hex(input):
            # Looks like an ID
            return cls.get(input)
        geom = geos_geom_from_string(input)
        return cls(geom, id=None)
