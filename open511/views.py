from functools import partial
import json

from django.contrib.gis.geos import Polygon
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import dateutil.parser

from open511.models import RoadEvent, Jurisdiction
from open511.utils.views import APIView, ModelListAPIView, Resource


def filter_status(qs, filter_type, value):
    if value == 'active':
        return qs.filter(active=True)
    elif value == 'archived':
        return qs.filter(active=False)


def filter_xpath(xpath, qs, filter_type, value, xml_field='xml_data', typecast='text'):
    return qs.extra(
        where=['(xpath(%s, {0}))::{1}[] @> ARRAY[%s]'.format(xml_field, typecast)],
        params=[xpath, value]
    )


def filter_datetime(fieldname, qs, filter_type, value, allowable_filters=['gt', 'gte', 'lt', 'lte']):
    value = dateutil.parser.parse(value)
    if filter_type in allowable_filters:
        query = '__'.join((fieldname, filter_type))
    else:
        query = fieldname
    return qs.filter(**{query: value})


def filter_bbox(qs, filter_type, value, fieldname='geom'):
    try:
        coords = [float(n) for n in value.split(',')]
    except ValueError:
        raise # FIXME
    assert len(coords) == 4
    return qs.filter(**{fieldname + '__intersects': Polygon.from_bbox(coords)})


class RoadEventListView(ModelListAPIView):

    allow_jsonp = True

    filters = {
        'status': filter_status,
        'eventType': partial(filter_xpath, 'eventType/text()'),
        'creationDate': partial(filter_datetime, 'created'),
        'lastUpdate': partial(filter_datetime, 'updated'),
        'bbox': filter_bbox,
        # FIXME jurisdiction
        # FIXME severity
        'eventSubType': partial(filter_xpath, 'eventSubType/text()'),
        'travelerMessage': partial(filter_xpath, 'travelerMessage/text()'),
        'roadName': partial(filter_xpath, 'roads/road/roadName/text()'),
        'city': partial(filter_xpath, 'roads/road/city/text()'),
        'impactedSystem': partial(filter_xpath, 'roads/road/impactedSystems/impactedSystem/text()'),
        # FIXME groupedEvent
        # FIXME schedule
    }

    def post_filter(self, request, qs):
        objects = super(RoadEventListView, self).post_filter(request, qs)
        if 'inEffectOn' in request.GET:
            # FIXME inefficient - implement on DB
            query = dateutil.parser.parse(request.GET['inEffectOn']).date()
            objects = filter(lambda o: o.schedule.includes(query), objects)
        return objects

    def get_qs(self, request, jurisdiction_slug=None):
        qs = RoadEvent.objects.all()
        if jurisdiction_slug:
            jur = get_object_or_404(Jurisdiction, slug=jurisdiction_slug)
            qs = qs.filter(jurisdiction=jur)

        if 'status' not in request.GET:
            # By default, show only active events
            qs = qs.filter(active=True)

        return qs

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(accept_language=request.accept_language)


class RoadEventView(APIView):

    def post(self, request, jurisdiction_slug, id):
        # FIXME security, abstraction
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        updates = json.loads(request.raw_post_data)

        for key, val in updates.items():
            rdev.update(key, val)

        rdev.full_clean()
        rdev.save()

        return self.get(request, jurisdiction_slug, id)

    def get(self, request, jurisdiction_slug, id):
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        return Resource(rdev.to_full_xml_element(accept_language=request.accept_language))


class JurisdictionListView(ModelListAPIView):

    allow_jsonp = True

    def get_qs(self, request):
        return Jurisdiction.objects.all()

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(accept_language=request.accept_language)


class JurisdictionView(APIView):

    def get(self, request, slug):
        jur = get_object_or_404(Jurisdiction, slug=slug)
        return Resource(jur.to_full_xml_element(accept_language=request.accept_language))


def unimplemented_view(request, *args, **kwargs):
    return HttpResponse('Not yet implemented')

list_roadevents = RoadEventListView.as_view()
roadevent = RoadEventView.as_view()
list_jurisdictions = JurisdictionListView.as_view()
jurisdiction = JurisdictionView.as_view()
