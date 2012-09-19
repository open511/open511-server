from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from open511.models import RoadEvent
from open511.utils.http import accept_language_from_request
from open511.utils.views import APIView, Resource, ResourceList


class RoadEventListView(APIView):

    allow_jsonp = True

    def get(self, request):
        if request.response_format == 'application/xml':
            # If we're outputting XML, don't prune languages by default
            accept_language = accept_language_from_request(request, default=None)
        else:
            accept_language = accept_language_from_request(request)
        resources = [
            rdev.to_full_xml_element(accept_language=accept_language)
            for rdev in RoadEvent.objects.all()
        ]
        return ResourceList(resources)


class RoadEventView(APIView):

    def get(self, request, jurisdiction_slug, id):
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        return Resource(rdev.to_full_xml_element())


def unimplemented_view(request, *args, **kwargs):
    return HttpResponse('Not yet implemented')

list_roadevents = RoadEventListView.as_view()
roadevent = RoadEventView.as_view()
list_jurisdictions = unimplemented_view
jurisdiction = unimplemented_view
