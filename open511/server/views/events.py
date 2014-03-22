import datetime
from functools import partial
import json

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

import dateutil.parser
from lxml.builder import E
from pytz import utc

from open511.server.models import RoadEvent, Jurisdiction, SearchGeometry
from open511.server.utils.auth import can
from open511.server.utils.exceptions import BadRequest
from open511.server.utils.views import APIView, ModelListAPIView, Resource
from open511.server.views import CommonFilters, CommonListView


def filter_status(qs, value):
    if value.lower() == 'active':
        return qs.filter(active=True)
    elif value.lower() == 'archived':
        return qs.filter(active=False)
    elif value.lower() in ('*', 'all'):
        return qs
    else:
        return qs.none()

class RoadEventListView(CommonListView):

    allow_jsonp = True

    model = RoadEvent

    resource_name_plural = 'events'

    filters = {
        'status': filter_status,
        'event_type': partial(CommonFilters.xpath, 'event_type/text()'),
        'created': partial(CommonFilters.datetime, 'created'),
        'updated': partial(CommonFilters.datetime, 'updated'),
        'bbox': CommonFilters.bbox,
        'jurisdiction': CommonFilters.jurisdiction,
        'severity': partial(CommonFilters.xpath, 'severity/text()'),
        'event_subtype': partial(CommonFilters.xpath, 'event_subtypes/event_subtype/text()'),
        'road_name': partial(CommonFilters.xpath, 'roads/road/name/text()'),
        'impacted_system': partial(CommonFilters.xpath, 'roads/road/impacted_systems/impacted_system/text()'),
        'id': partial(CommonFilters.db, 'id'),
        'area': partial(CommonFilters.xpath, 'areas/area/id/text()'),
        'area_name': partial(CommonFilters.xpath, 'areas/area/name/text()'),
        'geography': None,  # dealt with in post_filter
        'tolerance': None,  # dealth with in post_filter
        'in_effect_on': None,  # dealt with in post_filter
    }

    unauthenticated_methods = ModelListAPIView.unauthenticated_methods + (
        'POST',)

    def post_filter(self, request, qs):
        objects = super(RoadEventListView, self).post_filter(request, qs)

        if 'in_effect_on' in request.REQUEST:
            # FIXME inefficient - implement on DB
            if request.REQUEST['in_effect_on'] == 'now':
                start, end = utc.localize(datetime.datetime.utcnow()), None
            else:
                raw_start, _, raw_end = request.REQUEST['in_effect_on'].partition(',')
                start = dateutil.parser.parse(raw_start)
                end = dateutil.parser.parse(raw_end) if raw_end else None
            if end:
                if (end - start) > datetime.timedelta(days=40):
                    raise BadRequest("The in_effect_on filter can't handle ranges of more than 40 days.")
                filter_func = lambda o: o.schedule.active_within_range(start, end)
            else:
                filter_func = lambda o: o.schedule.includes(start)
            objects = filter(filter_func, objects)
        return objects

    def get_qs(self, request, jurisdiction_id=None):
        qs = super(RoadEventListView, self).get_qs(request, jurisdiction_id)

        if not can(request, 'view_internal'):
            qs = qs.filter(published=True)

        if 'status' not in request.REQUEST:
            # By default, show only active events
            qs = qs.filter(active=True)

        return qs

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(
            accept_language=request.accept_language,
            remove_internal_elements=not can(request, 'view_internal')
        )

    def post(self, request):
        if 'application/json' in request.META['CONTENT_TYPE']:
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

        jurisdiction_id = content.pop('jurisdiction_id')
        jurisdiction = Jurisdiction.objects.get(id=jurisdiction_id)

        if not jurisdiction.can_edit(request.user):
            raise PermissionDenied

        rdev = RoadEvent(jurisdiction=jurisdiction)
        for key, val in content.items():
            rdev.update(key, val)

        rdev.auto_label_areas()
        rdev.save()

        return HttpResponseRedirect(rdev.get_absolute_url())


class RoadEventView(APIView):

    model = RoadEvent

    def post(self, request, jurisdiction_id, id):
        if request.META.get('HTTP_X_HTTP_METHOD_OVERRIDE') == 'PATCH':
            return self.patch(request, jurisdiction_id, id)

        return HttpResponseNotAllowed(['GET', 'PATCH', 'DELETE'])

    def patch(self, request, jurisdiction_id, id):
        # FIXME security, abstraction
        rdev = get_object_or_404(RoadEvent, jurisdiction__id=jurisdiction_id, id=id)
        updates = json.loads(request.body)

        if not rdev.jurisdiction.can_edit(request.user):
            raise PermissionDenied

        for key, val in updates.items():
            rdev.update(key, val)

        rdev.full_clean()
        rdev.save()

        return self.get(request, jurisdiction_id, id)

    def delete(self, request, jurisdiction_id, id):
        rdev = get_object_or_404(RoadEvent, jurisdiction__id=jurisdiction_id, id=id)

        if not rdev.jurisdiction.can_edit(request.user):
            raise PermissionDenied

        rdev.delete()

        return HttpResponse(status=204)

    def get(self, request, jurisdiction_id, id):
        base_qs = RoadEvent.objects.filter(jurisdiction__id=jurisdiction_id)
        if not can(request, 'view_internal'):
            base_qs = base_qs.filter(published=True)
        try:
            rdev = base_qs.get(id=id)
        except RoadEvent.DoesNotExist:
            raise Http404
        return Resource(E.events(rdev.to_full_xml_element(
            accept_language=request.accept_language,
            remove_internal_elements=not can(request, 'view_internal')
        )))

list_roadevents = RoadEventListView.as_view()
roadevent = RoadEventView.as_view()
