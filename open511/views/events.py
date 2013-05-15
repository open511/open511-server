import datetime
from functools import partial
import json
from urllib import urlencode

from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import Distance
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

import dateutil.parser
from pytz import utc

from open511.models import RoadEvent, Jurisdiction, SearchGeometry
from open511.utils.views import APIView, ModelListAPIView, Resource


def filter_status(qs, value):
    if value.lower() == 'active':
        return qs.filter(active=True)
    elif value.lower() == 'archived':
        return qs.filter(active=False)
    elif value.lower() in ('*', 'all'):
        return qs
    else:
        return qs.none()


def filter_xpath(xpath, qs, value, xml_field='xml_data', typecast='text'):
    return qs.extra(
        where=['(xpath(%s, {0}))::{1}[] @> ARRAY[%s]'.format(xml_field, typecast)],
        params=[xpath, value]
    )


def filter_db(fieldname, qs, value, allow_operators=False):
    if allow_operators:
        operator, value = _parse_operator_from_value(value)
        fieldname = fieldname + '__' + operator
    return qs.filter(**{fieldname: value})


def filter_datetime(fieldname, qs, value):
    query_type, value = _parse_operator_from_value(value)
    value = dateutil.parser.parse(value)
    if not value.tzinfo:
        raise ValueError("Time-based filters must provide a timezone")
    return qs.filter(**{'__'.join((fieldname, query_type)): value})


def filter_bbox(qs, value, fieldname='geom'):
    coords = [float(n) for n in value.split(',')]
    assert len(coords) == 4
    return qs.filter(**{fieldname + '__intersects': Polygon.from_bbox(coords)})

def filter_geography(qs, value, within=None):
    search_geom = SearchGeometry.fromstring(value)
    if within is not None:
        return qs.filter(geom__dwithin=(search_geom.geom, Distance(m=within)))
    return qs.filter(geom__intersects=search_geom.geom)

def filter_jurisdiction(qs, value):
    # The jurisdiction parameter can be:
    # - A full http:// URL to the external jurisdiction
    # - Some kind relative URL: /api/jurisdictions/mtq
    # - Just the slug: mtq
    return qs.filter(Q(jurisdiction__external_url=value) | 
        Q(jurisdiction__slug=value.rstrip('/').split('/')[-1]))

FILTER_OPERATORS = [
    ('<=', 'lte'),
    ('>=', 'gte'),
    ('<', 'lt'),
    ('>', 'gt')
]
def _parse_operator_from_value(value):
    for op, query_type in FILTER_OPERATORS:
        if value.startswith(op):
            return query_type, value[len(op):]
    return 'exact', value


class RoadEventListView(ModelListAPIView):

    allow_jsonp = True

    model = RoadEvent

    filters = {
        'status': filter_status,
        'event_type': partial(filter_xpath, 'event_type/text()'),
        'created': partial(filter_datetime, 'created'),
        'updated': partial(filter_datetime, 'updated'),
        'bbox': filter_bbox,
        'jurisdiction': filter_jurisdiction,
        'severity': partial(filter_db, 'severity', allow_operators=True),
        'event_subtype': partial(filter_xpath, 'event_subtype/text()'),
        'road_name': partial(filter_xpath, 'roads/road/road_name/text()'),
        'impacted_system': partial(filter_xpath, 'roads/road/impacted_systems/impacted_system/text()'),
        'id': partial(filter_db, 'id'),
        'geography': None,  # dealt with in post_filter
        'tolerance': None,  # dealth with in post_filter
        'in_effect_on': None,  # dealt with in post_filter
    }

    unauthenticated_methods = ModelListAPIView.unauthenticated_methods + (
        'POST',)

    def post_filter(self, request, qs):
        objects = super(RoadEventListView, self).post_filter(request, qs)

        if 'geography' in request.REQUEST:
            objects = filter_geography(objects, request.REQUEST['geography'],
                within=request.REQUEST.get('tolerance'))

        if 'in_effect_on' in request.REQUEST:
            # FIXME inefficient - implement on DB
            if request.REQUEST['in_effect_on'] == 'now':
                start, end = utc.localize(datetime.datetime.utcnow()), None
            else:
                raw_start, _, raw_end = request.REQUEST['in_effect_on'].partition(',')
                start = dateutil.parser.parse(raw_start)
                end = dateutil.parser.parse(raw_end) if raw_end else None
            if end:
                filter_func = lambda o: o.schedule.active_within_range(start, end)
            else:
                filter_func = lambda o: o.schedule.includes(start)
            objects = filter(filter_func, objects)
        return objects

    def get_qs(self, request, jurisdiction_slug=None):
        qs = RoadEvent.objects.all()
        if jurisdiction_slug:
            jur = get_object_or_404(Jurisdiction, slug=jurisdiction_slug)
            qs = qs.filter(jurisdiction=jur)

        if 'status' not in request.REQUEST:
            # By default, show only active events
            qs = qs.filter(active=True)

        return qs

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(accept_language=request.accept_language)

    def post(self, request):
        if request.META['CONTENT_TYPE'] == 'application/json':
            return self.post_to_create(request)

        opts = request.POST.copy()
        if 'geography' in opts and len(opts['geography']) > 1000:
            sgeom = SearchGeometry.fromstring(opts['geography'])
            sgeom.save()
            opts['geography'] = sgeom.id

        return HttpResponseRedirect('?' + opts.urlencode())


    def post_to_create(self, request):
        if not request.user.is_authenticated():
            raise PermissionDenied
        content = json.loads(request.body)

        jurisdiction_url = content.pop('jurisdiction_url')
        jurisdiction = Jurisdiction.objects.get(
            Q(external_url=jurisdiction_url) |
            Q(slug=filter(None, jurisdiction_url.split('/'))[-1])
        )

        if not jurisdiction.can_edit(request.user):
            raise PermissionDenied

        rdev = RoadEvent(jurisdiction=jurisdiction)
        for key, val in content.items():
            rdev.update(key, val)
        rdev.save()

        return HttpResponseRedirect(rdev.get_absolute_url())


class RoadEventView(APIView):

    model = RoadEvent

    def patch(self, request, jurisdiction_slug, id):
        # FIXME security, abstraction
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        updates = json.loads(request.raw_post_data)

        if not rdev.jurisdiction.can_edit(request.user):
            raise PermissionDenied

        for key, val in updates.items():
            rdev.update(key, val)

        rdev.full_clean()
        rdev.save()

        return self.get(request, jurisdiction_slug, id)

    def get(self, request, jurisdiction_slug, id):
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        return Resource(rdev.to_full_xml_element(accept_language=request.accept_language))

list_roadevents = RoadEventListView.as_view()
roadevent = RoadEventView.as_view()
